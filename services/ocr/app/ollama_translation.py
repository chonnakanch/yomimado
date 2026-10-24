"""Local Ollama adapter. Only explicit pulls download models; chat sends text only."""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request

MODEL_NAME = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)?(?::[A-Za-z0-9_.-]+)?"
)
MAX_RESPONSE = 1024 * 1024
CONTROL_TOKEN = re.compile(r"<\s*[|｜]+|<\s*(?:[|｜\ufffd]\s*)*hy[_-]", re.IGNORECASE)


def model_name(value: str) -> str:
    if not MODEL_NAME.fullmatch(value) or len(value) > 200:
        raise ValueError("Enter an Ollama model name, such as namespace/model:tag")
    if "cloud" in value.lower().split(":")[-1]:
        raise ValueError("Choose a local Ollama model; cloud models are not supported")
    return value if ":" in value else value + ":latest"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise ValueError("Ollama must respond locally without redirects")


def open_request(path: str, body: dict | None = None, timeout: int = 5):
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        # Ignore system proxies: Japanese text must stay on loopback.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        return opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            "Ollama could not complete the request. Check the model name and available memory."
        ) from error
    except OSError as error:
        raise RuntimeError(
            "Could not connect to Ollama. Install and open Ollama, then try again."
        ) from error


def request_json(path: str, body: dict | None = None, timeout: int = 5) -> dict:
    with open_request(path, body, timeout) as response:
        data = response.read(MAX_RESPONSE + 1)
    if len(data) > MAX_RESPONSE:
        raise ValueError("Ollama returned too much data")
    value = json.loads(data)
    if not isinstance(value, dict) or value.get("error"):
        raise ValueError("Ollama could not complete the request")
    return value


def installed_models() -> list[dict]:
    models = request_json("tags").get("models")
    if not isinstance(models, list):
        raise TypeError("Ollama returned an invalid model list")
    result = []
    for model in models:
        if not isinstance(model, dict):
            continue
        try:
            if model.get("remote_model") or model.get("remote_host"):
                continue
            name = model_name(model["name"])
            digest = model["digest"]
            if not isinstance(digest, str) or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", digest):
                raise ValueError("Invalid Ollama model digest")
            result.append({"name": name, "digest": digest})
        except (ValueError, KeyError, TypeError):
            continue
    return result


def local_model(name: str) -> dict:
    name = model_name(name)
    model = next((item for item in installed_models() if item["name"] == name), None)
    if model is None:
        raise ValueError("Download this model in Ollama before selecting it")
    info = request_json("show", {"model": name})
    if info.get("remote_model") or info.get("remote_host"):
        raise ValueError("Choose a local Ollama model; cloud models are not supported")
    capabilities = info.get("capabilities")
    if not isinstance(capabilities, list) or "completion" not in capabilities:
        raise ValueError("Choose an Ollama model that supports text generation")
    template = info.get("template")
    metadata = info.get("model_info")
    metadata = metadata if isinstance(metadata, dict) else {}
    # HY-MT2's vocabulary differs from older Hunyuan models. Some Ollama
    # imports carry a legacy template despite having the new token IDs.
    hy_mt2 = (
        metadata.get("general.architecture") == "hunyuan-dense"
        and metadata.get("tokenizer.ggml.bos_token_id") == 127958
        and metadata.get("tokenizer.ggml.eot_token_id") == 127960
        and metadata.get("tokenizer.ggml.seperator_token_id") == 127962
    )
    return model | {"template": template if isinstance(template, str) else "", "hy_mt2": hy_mt2}


class OllamaProvider:
    def __init__(self, name: str):
        self.name = model_name(name)

    @property
    def identity(self) -> str:
        # Prompt changes must not reuse answers cached under the old contract.
        return "ollama-ja-en-v3:" + self.name + ":" + local_model(self.name)["digest"]

    def translate(self, text: str) -> str:
        # Check again immediately before sending text, including renamed cloud aliases.
        model = local_model(self.name)
        options = {"temperature": 0, "num_predict": 512}
        instruction = (
            "Translate the following segment into English, without additional explanation.\n\n"
            + text
        )
        if model["hy_mt2"]:
            # Render the publisher's single-user format directly, bypassing a
            # stale Ollama template. Keep stop strings in this vocabulary too.
            options["stop"] = ["<|eos|>", "<|extra_5|>", "<|startoftext|>"]
            value = request_json(
                "generate",
                {
                    "model": self.name,
                    "raw": True,
                    "stream": False,
                    "prompt": "<|startoftext|>" + instruction + "<|extra_0|>",
                    "options": options,
                },
                timeout=120,
            )
            output = value.get("response")
        else:
            value = self._chat(model, instruction, options)
            message = value.get("message")
            output = message.get("content") if isinstance(message, dict) else None
        if (
            value.get("done") is not True
            or value.get("done_reason") == "length"
            or not isinstance(output, str)
            or not output.strip()
        ):
            raise RuntimeError("Ollama returned no complete translation. Try another text model.")
        if "\ufffd" in output or CONTROL_TOKEN.search(output):
            # Reject rather than trim an uncertain prefix and cache it as a
            # translation. The API error leaves the original Japanese visible.
            raise RuntimeError(
                "Ollama returned malformed translation text. Check the model template or choose another local text model."
            )
        return output.strip()

    def _chat(self, model: dict, instruction: str, options: dict) -> dict:
        if "<｜hy_User｜>" in model["template"]:
            # Some Hunyuan Ollama templates only stop at no-8. The model can
            # instead begin an invented next turn, even after a good translation.
            options["stop"] = [
                "<｜hy_User｜>",
                "<｜hy_Assistant｜>",
                "<｜hy_place▁holder▁no▁2｜>",
                "<｜hy_place▁holder▁no▁8｜>",
            ]
        return request_json(
            "chat",
            {
                "model": self.name,
                "stream": False,
                "messages": [
                    {
                        # Translation models such as HY-MT expect the task in the
                        # user turn. A bare question can otherwise get answered.
                        "role": "user",
                        "content": instruction,
                    },
                ],
                "options": options,
            },
            timeout=120,
        )


class OllamaDownloads:
    def __init__(self):
        self.lock = threading.Lock()
        self.job = {"state": "idle", "model": "", "message": "", "completed": 0, "total": 0}

    def status(self) -> dict:
        with self.lock:
            return self.job.copy()

    def start(self, name: str) -> dict:
        name = model_name(name)
        with self.lock:
            if self.job["state"] == "downloading":
                if self.job["model"] != name:
                    raise ValueError("Wait for the current Ollama download to finish")
            else:
                self.job = {
                    "state": "downloading",
                    "model": name,
                    "message": "Starting download…",
                    "completed": 0,
                    "total": 0,
                }
                threading.Thread(target=self._pull, args=(name,), daemon=True).start()
        return self.status()

    def _pull(self, name: str):
        try:
            success = False
            with open_request("pull", {"model": name, "stream": True}, timeout=60) as stream:
                while line := stream.readline(MAX_RESPONSE + 1):
                    if len(line) > MAX_RESPONSE:
                        raise ValueError("Ollama returned an invalid download update")
                    value = json.loads(line)
                    if not isinstance(value, dict) or value.get("error"):
                        raise ValueError(
                            "Download failed. Check the model name, connection and disk space."
                        )
                    total, completed = value.get("total", 0), value.get("completed", 0)
                    if (
                        type(total) is not int
                        or type(completed) is not int
                        or not 0 <= completed <= total
                    ):
                        raise ValueError("Ollama returned invalid download progress")
                    with self.lock:
                        self.job.update(
                            message=str(value.get("status", "Downloading…")),
                            total=total,
                            completed=completed,
                        )
                    if value.get("status") == "success":
                        success = True
            if not success:
                raise ValueError("Download interrupted. Try again to resume it.")
            local_model(name)
            with self.lock:
                self.job.update(
                    state="ready", message="Downloaded. Choose Use this model to translate with it."
                )
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            with self.lock:
                self.job.update(state="error", message=str(error))


downloads = OllamaDownloads()
