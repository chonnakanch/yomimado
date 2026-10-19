"""Isolated cached OCR/CoreML adapters; production factories do not import this."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np


def parent_rows(previous: np.ndarray, current: np.ndarray) -> np.ndarray:
    """Find selected beam parents without changing the existing generation policy.

    Identical prefix rows have identical caches for this deterministic eval model.
    Every tensor (self and cross attention) must follow the selected parent rows.
    """
    if current.shape != (len(previous), previous.shape[1] + 1):
        raise ValueError("Cached decoding requires exactly one new token per beam")
    parents = []
    for prefix in current[:, :-1]:
        matches = np.flatnonzero(np.all(previous == prefix, axis=1))
        if not len(matches):
            raise ValueError("Selected beam prefix is absent from the previous step")
        parents.append(matches[0])
    return np.asarray(parents, dtype=np.int64)


class CachedStep:
    def __init__(self, prefill, decoder, hidden):
        self.prefill, self.decoder, self.hidden = prefill, decoder, hidden
        self.previous = None
        self.cache = None

    def __call__(self, ids):
        if self.previous is None:
            if ids.shape[1] != 1:
                raise ValueError("Prefill requires the one-token OCR prompt")
            outputs = self.prefill.run(
                None,
                {
                    "input_ids": ids,
                    "encoder_hidden_states": np.repeat(self.hidden, len(ids), axis=0),
                },
            )
        else:
            parents = parent_rows(self.previous, ids)
            feeds = {"input_ids": ids[:, -1:]}
            # Encoder hidden states may be pruned: cross K/V already supply them.
            for item in self.decoder.get_inputs():
                if item.name == "encoder_hidden_states":
                    feeds[item.name] = np.repeat(self.hidden, len(ids), axis=0)
                elif item.name.startswith("past_"):
                    feeds[item.name] = self.cache[item.name.removeprefix("past_")][
                        parents
                    ]
            outputs = self.decoder.run(None, feeds)
        self.cache = {
            item.name.removeprefix("present_"): value
            for item, value in zip(
                (
                    item
                    for item in (
                        self.prefill if self.previous is None else self.decoder
                    ).get_outputs()
                    if item.name != "logits"
                ),
                outputs[1:],
            )
        }
        self.previous = ids.copy()
        return outputs[0][:, -1, :]


def session(path: Path, coreml: bool, cache: Path, profile=False):
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.enable_profiling = profile
    cache.mkdir(parents=True, exist_ok=True)
    options.profile_file_prefix = str(cache / path.stem)
    providers = ["CPUExecutionProvider"]
    if coreml:
        with path.open("rb") as stream:
            graph_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        weights = path.parent / "decoder-weights.bin"
        if path.name in ("ocr-cached.onnx", "ocr-prefill.onnx"):
            with weights.open("rb") as stream:
                weight_hash = hashlib.file_digest(stream, "sha256").hexdigest()
            graph_hash = hashlib.sha256((graph_hash + weight_hash).encode()).hexdigest()
        providers.insert(
            0,
            (
                "CoreMLExecutionProvider",
                {
                    "ModelFormat": "MLProgram",
                    "MLComputeUnits": "ALL",
                    "RequireStaticInputShapes": "0",
                    "EnableOnSubgraphs": "0",
                    "ModelCacheDirectory": str((cache / graph_hash).resolve()),
                },
            ),
        )
    started = time.perf_counter()
    result = ort.InferenceSession(str(path), options, providers=providers)
    result.disable_fallback()
    if coreml and "CoreMLExecutionProvider" not in result.get_providers():
        raise RuntimeError("CoreML session initialization fell back to CPU")
    return result, (time.perf_counter() - started) * 1000


def profile_summary(session):
    path = session.end_profiling()
    events = json.loads(Path(path).read_text())
    providers = {}
    for event in events:
        provider = event.get("args", {}).get("provider")
        if (
            event.get("cat") == "Node"
            and provider
            and event["name"].endswith("_kernel_time")
        ):
            item = providers.setdefault(
                provider, {"calls": 0, "durationUs": 0, "nodes": set()}
            )
            item["calls"] += 1
            item["durationUs"] += event["dur"]
            item["nodes"].add(event["name"])
    for item in providers.values():
        item["nodes"] = sorted(item["nodes"])
    return {"path": path, "providers": providers}


def recognizer(
    model,
    exports,
    cached,
    cache,
    coreml_encoder=False,
    coreml_decoder=False,
    profile=False,
):
    # Retain the existing image preprocessing, tokenizer, generation and cleanup.
    class Recognizer:
        def __init__(self):
            from app.pipeline.ocr_tokenizer import load_ocr_tokenizer
            from onnx_generation import Policy
            from transformers import ViTImageProcessor

            self.encoder, encoder_ms = session(
                exports / "ocr-encoder.onnx", coreml_encoder, cache, profile
            )
            self.decoder, decoder_ms = session(
                (cached / "ocr-cached.onnx")
                if cached
                else (exports / "ocr-decoder.onnx"),
                coreml_decoder,
                cache,
                profile,
            )
            self.prefill = None
            prefill_ms = 0
            if cached:
                self.prefill, prefill_ms = session(
                    cached / "ocr-prefill.onnx", coreml_decoder, cache, profile
                )
            self.processor = ViTImageProcessor.from_pretrained(
                model, local_files_only=True
            )
            self.tokenizer = load_ocr_tokenizer(model)
            self.policy = Policy(
                **json.loads((exports / "policies.json").read_text())["ocr"]
            )
            self.load_ms = {
                "encoder": encoder_ms,
                "decoder": decoder_ms,
                "prefill": prefill_ms,
            }
            self.last_tokens = None

        def __call__(self, image):
            import re

            import jaconv
            from onnx_generation import beam_search

            pixels = self.processor(
                image.convert("L").convert("RGB"), return_tensors="np"
            ).pixel_values
            hidden = self.encoder.run(None, {"pixel_values": pixels})[0]
            if self.prefill:
                step = CachedStep(self.prefill, self.decoder, hidden)
            else:

                def step(ids):
                    return self.decoder.run(
                        None,
                        {
                            "input_ids": ids,
                            "encoder_hidden_states": np.repeat(
                                hidden, len(ids), axis=0
                            ),
                        },
                    )[0][:, -1, :]

            self.last_tokens = beam_search(step, self.policy)
            text = self.tokenizer.decode(self.last_tokens, skip_special_tokens=True)
            text = "".join(text.split()).replace("…", "...")
            text = re.sub(
                "[・.]{2,}", lambda match: (match.end() - match.start()) * ".", text
            )
            return jaconv.h2z(text, ascii=True, digit=True)

    return Recognizer()
