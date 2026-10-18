"""Private, hash-pinned OCR cache export; never a release packaging command.

Exports prefill and single-token decoder graphs with shared external weights.
Uses the already installed Torch/ONNX tools and local model files only.
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
from transformers import EncoderDecoderCache

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class CachedDecoder(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.decoder = model.decoder

    def forward(self, input_ids, encoder_hidden_states, *flat_cache):
        cache = (
            EncoderDecoderCache.from_legacy_cache(
                tuple(
                    tuple(flat_cache[i : i + 4]) for i in range(0, len(flat_cache), 4)
                )
            )
            if flat_cache
            else None
        )
        output = self.decoder(
            input_ids=input_ids,
            encoder_hidden_states=encoder_hidden_states,
            past_key_values=cache,
            use_cache=True,
            return_dict=True,
        )
        return (output.logits,) + tuple(
            tensor
            for layer in output.past_key_values.to_legacy_cache()
            for tensor in layer
        )


def share_weights(paths):
    """Write unique initializer bytes once, retaining dtype/shape in each graph."""
    locations = {}
    weights = paths[0].parent / "decoder-weights.bin"
    with weights.open("xb") as stream:
        for path in paths:
            model = onnx.load(path)
            for tensor in model.graph.initializer:
                if not tensor.raw_data:
                    continue
                data = tensor.raw_data
                key = hashlib.sha256(data).hexdigest()
                if key not in locations:
                    offset = stream.tell()
                    stream.write(data)
                    locations[key] = (offset, len(data))
                offset, length = locations[key]
                onnx.external_data_helper.set_external_data(
                    tensor, weights.name, offset=offset, length=length
                )
                tensor.ClearField("raw_data")
            onnx.save_model(model, path)
    for path in paths:
        onnx.checker.check_model(str(path))


def export(model_path, output):
    pins = json.loads((ROOT / "services/ocr/windows-assets.json").read_text())
    inputs = {}
    for asset in pins:
        if asset["path"].startswith("manga-ocr-base/"):
            name = asset["path"].split("/", 1)[1]
            actual = digest(model_path / name)
            if actual != asset["sha256"]:
                raise ValueError("Unverified OCR model input: " + name)
            inputs[name] = actual
    # Refuse reuse: stale external offsets or partially overwritten graphs are unsafe.
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    model = MangaOcrModel.from_pretrained(
        model_path, local_files_only=True, attn_implementation="eager"
    ).eval()
    wrapper = CachedDecoder(model).eval()
    config = model.decoder.config
    if config.model_type != "bert" or config.num_hidden_layers != 2:
        raise ValueError(
            "This experiment only supports the pinned two-layer OCR decoder"
        )
    cache_names = [
        f"{kind}_{layer}_{slot}"
        for layer in range(config.num_hidden_layers)
        for kind, slot in (
            ("self", "key"),
            ("self", "value"),
            ("cross", "key"),
            ("cross", "value"),
        )
    ]
    output_names = ["logits"] + ["present_" + name for name in cache_names]
    ids = torch.tensor([[model.generation_config.decoder_start_token_id]])
    with torch.inference_mode():
        hidden = model.encoder(pixel_values=torch.zeros((1, 3, 224, 224)))[0]
        prefill = wrapper(ids, hidden)
        paths = []
        for cached in (False, True):
            path = output / ("ocr-cached.onnx" if cached else "ocr-prefill.onnx")
            names = ["input_ids", "encoder_hidden_states"]
            axes = {"input_ids": {0: "beams"}, "encoder_hidden_states": {0: "beams"}}
            args = (ids, hidden)
            if cached:
                names += ["past_" + name for name in cache_names]
                args += prefill[1:]
            for name in names + output_names:
                if "self_" in name:
                    axes[name] = {
                        0: "beams",
                        2: "present_length"
                        if name.startswith("present")
                        else "past_length",
                    }
                elif "cross_" in name or name == "logits":
                    axes[name] = {0: "beams"}
            torch.onnx.export(
                wrapper,
                args,
                str(path),
                input_names=names,
                output_names=output_names,
                dynamic_axes=axes,
                opset_version=17,
                dynamo=False,
            )
            paths.append(path)
    share_weights(paths)
    report = {
        "sourceInputs": inputs,
        "exporterSha256": digest(Path(__file__)),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("torch", "transformers", "onnx")
        },
        "outputs": {
            path.name: {"sha256": digest(path), "bytes": path.stat().st_size}
            for path in sorted(output.iterdir())
        },
        "cacheNames": cache_names,
        "publicDistributionApproved": False,
    }
    (output / "export.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(args.model.resolve(), args.output.resolve())
