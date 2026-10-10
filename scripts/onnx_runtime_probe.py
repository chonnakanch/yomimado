"""Torch-free inference adapters for the Windows backend feasibility experiment."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jaconv
import numpy as np
import onnxruntime as ort
from onnx_generation import Policy, beam_search
from PIL import Image
from transformers import AutoTokenizer, ViTImageProcessor


def session(path: Path) -> ort.InferenceSession:
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    return ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


class OnnxRecognizer:
    def __init__(self, model: Path, exported: Path):
        self.encoder = session(exported / "ocr-encoder.onnx")
        self.decoder = session(exported / "ocr-decoder.onnx")
        self.processor = ViTImageProcessor.from_pretrained(model, local_files_only=True)
        self.tokenizer = AutoTokenizer.from_pretrained(
            model, tokenizer_type="bert-japanese", local_files_only=True
        )
        config = json.loads((exported / "policies.json").read_text(encoding="utf-8"))[
            "ocr"
        ]
        self.policy = Policy(**config)

    def __call__(self, image: Image.Image) -> str:
        pixels = self.processor(
            image.convert("L").convert("RGB"), return_tensors="np"
        ).pixel_values
        hidden = self.encoder.run(None, {"pixel_values": pixels})[0]

        def step(ids: np.ndarray) -> np.ndarray:
            return self.decoder.run(
                None,
                {
                    "input_ids": ids,
                    "encoder_hidden_states": np.repeat(hidden, len(ids), axis=0),
                },
            )[0][:, -1, :]

        tokens = beam_search(step, self.policy)
        text = self.tokenizer.decode(tokens, skip_special_tokens=True)
        # Manga OCR 0.1.16 post_process semantics, without importing its Torch module.
        text = "".join(text.split()).replace("…", "...")
        text = re.sub(
            "[・.]{2,}", lambda match: (match.end() - match.start()) * ".", text
        )
        return jaconv.h2z(text, ascii=True, digit=True)


class OnnxTranslation:
    def __init__(self, model: Path, exported: Path):
        self.encoder = session(exported / "translation-encoder.onnx")
        self.decoder = session(exported / "translation-decoder.onnx")
        self.tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True)
        config = json.loads((exported / "policies.json").read_text(encoding="utf-8"))[
            "translation"
        ]
        config["banned"] = tuple(config["banned"])
        self.policy = Policy(**config)
        self.exported = exported

    @property
    def identity(self) -> str:
        # Experimental cache identity cannot mask a baseline translation with a hit.
        return "onnx-prototype:" + str(self.exported.resolve())

    def translate(self, text: str) -> str:
        inputs = self.tokenizer(text, return_tensors="np")
        if inputs.input_ids.shape[1] > 512:
            raise ValueError(
                "The selected sentence is too long for the local translator"
            )
        hidden = self.encoder.run(None, dict(inputs))[0]

        def step(ids: np.ndarray) -> np.ndarray:
            return self.decoder.run(
                None,
                {
                    "input_ids": ids,
                    "encoder_hidden_states": np.repeat(hidden, len(ids), axis=0),
                    "encoder_attention_mask": np.repeat(
                        inputs.attention_mask, len(ids), axis=0
                    ),
                },
            )[0][:, -1, :]

        output = self.tokenizer.decode(
            beam_search(step, self.policy), skip_special_tokens=True
        ).strip()
        if not output:
            raise RuntimeError("The local translator returned an empty sentence")
        return output
