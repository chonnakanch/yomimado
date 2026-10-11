"""Export the existing hash-pinned OCR/translation models for an isolated probe.

Uses installed prebuilt Torch for conversion only. Never exports or copies the
user-installed detector weights. This is not a release packaging command.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import onnx
import torch
from manga_ocr.ocr import MangaOcrModel
from transformers import AutoModelForSeq2SeqLM

ROOT = Path(__file__).resolve().parent.parent


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_models(ocr: Path, translation: Path) -> dict:
    manifest = json.loads(
        (ROOT / "services/ocr/windows-assets.json").read_text(encoding="utf-8")
    )
    verified = {}
    for key, directory in (("manga-ocr-base", ocr), ("opus-mt-ja-en", translation)):
        for asset in manifest:
            if not asset["path"].startswith(key + "/"):
                continue
            name, expected = asset["path"].split("/", 1)[1], asset["sha256"]
            actual = digest(directory / name)
            if actual != expected:
                raise ValueError("Model input hash differs: " + key + "/" + name)
            verified[key + "/" + name] = actual
    return verified


class Encoder(torch.nn.Module):
    def __init__(self, model, vision):
        super().__init__()
        self.model, self.vision = model, vision

    def forward(self, inputs, attention_mask=None):
        if self.vision:
            return self.model.encoder(pixel_values=inputs, return_dict=False)[0]
        return self.model.model.encoder(
            input_ids=inputs, attention_mask=attention_mask, return_dict=False
        )[0]


class Decoder(torch.nn.Module):
    def __init__(self, model, vision):
        super().__init__()
        self.model, self.vision = model, vision

    def forward(self, input_ids, encoder_hidden_states, encoder_attention_mask=None):
        if self.vision:
            return self.model.decoder(
                input_ids=input_ids,
                encoder_hidden_states=encoder_hidden_states,
                use_cache=False,
                return_dict=False,
            )[0]
        states = self.model.model.decoder(
            input_ids=input_ids,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=encoder_attention_mask,
            use_cache=False,
            return_dict=False,
        )[0]
        return self.model.lm_head(states) + self.model.final_logits_bias


def export(ocr: Path, translation: Path, output: Path) -> None:
    verified = verify_models(ocr, translation)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(2)
    policies = {}
    for kind, model_path in (("ocr", ocr), ("translation", translation)):
        vision = kind == "ocr"
        cls = MangaOcrModel if vision else AutoModelForSeq2SeqLM
        print("Exporting pinned " + kind, flush=True)
        model = cls.from_pretrained(
            str(model_path), local_files_only=True, attn_implementation="eager"
        ).eval()
        config = model.generation_config
        policies[kind] = {
            "start": config.decoder_start_token_id,
            "eos": config.eos_token_id,
            "beams": config.num_beams,
            "limit": 300 if vision else 257,
            "length_penalty": config.length_penalty,
            "early_stopping": config.early_stopping,
            "no_repeat_ngram": config.no_repeat_ngram_size,
            "banned": [item[0] for item in (config.bad_words_ids or [])],
            "forced_eos": config.forced_eos_token_id is not None,
            "renormalize": config.renormalize_logits,
        }
        if (
            config.do_sample
            or config.num_beam_groups != 1
            or any(len(item) != 1 for item in (config.bad_words_ids or []))
        ):
            raise ValueError("Unsupported pinned generation policy")
        inputs = (
            torch.zeros((1, 3, 224, 224)) if vision else torch.tensor([[100, 200, 0]])
        )
        mask = torch.ones_like(inputs) if not vision else None
        encoder = Encoder(model, vision)
        encoder_args = (inputs,) if vision else (inputs, mask)
        encoder_names = ["pixel_values"] if vision else ["input_ids", "attention_mask"]
        axes = {} if vision else {name: {1: "source_length"} for name in encoder_names}
        with torch.inference_mode():
            hidden = encoder(*encoder_args)
            torch.onnx.export(
                encoder,
                encoder_args,
                str(output / (kind + "-encoder.onnx")),
                input_names=encoder_names,
                output_names=["hidden_states"],
                dynamic_axes=axes,
                opset_version=17,
                dynamo=False,
            )
            ids = torch.tensor([[config.decoder_start_token_id, 100]])
            decoder_args = (ids, hidden) if vision else (ids, hidden, mask)
            decoder_names = ["input_ids", "encoder_hidden_states"]
            axes = {
                "input_ids": {0: "beams", 1: "target_length"},
                "encoder_hidden_states": {0: "beams"},
            }
            if not vision:
                decoder_names.append("encoder_attention_mask")
                axes["encoder_hidden_states"][1] = "source_length"
                axes["encoder_attention_mask"] = {0: "beams", 1: "source_length"}
            torch.onnx.export(
                Decoder(model, vision),
                decoder_args,
                str(output / (kind + "-decoder.onnx")),
                input_names=decoder_names,
                output_names=["logits"],
                dynamic_axes=axes,
                opset_version=17,
                dynamo=False,
            )
        del model
    (output / "policies.json").write_text(
        json.dumps(policies, indent=2) + "\n", encoding="utf-8"
    )
    graphs = list(output.glob("*.onnx"))
    if len(graphs) != 4:
        raise RuntimeError("Expected exactly four exported graphs")
    for graph in graphs:
        onnx.checker.check_model(str(graph))
    report = {
        "sourceInputs": verified,
        "exporterSha256": digest(Path(__file__)),
        "versions": {
            p: importlib.metadata.version(p) for p in ("torch", "transformers", "onnx")
        },
        "outputs": {
            path.name: digest(path) for path in [*graphs, output / "policies.json"]
        },
        "publicDistributionApproved": False,
    }
    (output / "export.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-model", type=Path, required=True)
    parser.add_argument("--translation-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(args.ocr_model, args.translation_model, args.output)
