import io
import json
import threading

import pytest

from app import ollama_translation as ollama

DIGEST = "a" * 64


def test_model_list_excludes_remote_aliases_and_cloud_tags(monkeypatch):
    monkeypatch.setattr(
        ollama,
        "request_json",
        lambda _: {
            "models": [
                None,
                {"name": "my-model:latest", "digest": DIGEST},
                {
                    "name": "remote-alias:latest",
                    "digest": DIGEST,
                    "remote_host": "https://ollama.com",
                },
                {"name": "remote-model:latest", "digest": DIGEST, "remote_model": "remote"},
                {"name": "model:cloud", "digest": DIGEST},
            ]
        },
    )
    assert ollama.installed_models() == [{"name": "my-model:latest", "digest": DIGEST}]


def model_responses(path, body=None, timeout=5):
    if path == "tags":
        return {"models": [{"name": "my-model:latest", "digest": DIGEST}]}
    if path == "show":
        return {"capabilities": ["completion"]}
    if path == "chat":
        return {"done": True, "message": {"content": "School."}}
    pytest.fail("Unexpected Ollama request: " + path)


@pytest.mark.parametrize(
    "name",
    [
        "http://remote/model",
        "server:11434/model",
        "../model",
        "model\n",
        "gpt-oss:120b-cloud",
        "model:cloud",
    ],
)
def test_model_names_cannot_choose_remote_or_cloud_endpoints(name):
    with pytest.raises(ValueError):
        ollama.model_name(name)


def test_translation_is_explicit_text_only_and_uses_local_model_digest(monkeypatch):
    calls = []

    def request(path, body=None, timeout=5):
        calls.append((path, body))
        return model_responses(path, body, timeout)

    monkeypatch.setattr(ollama, "request_json", request)
    provider = ollama.OllamaProvider("my-model")
    assert calls == []
    assert provider.identity == "ollama-ja-en-v3:my-model:latest:" + DIGEST
    assert not any(path == "chat" for path, _ in calls)
    assert provider.translate("学校。") == "School."
    chat = next(body for path, body in calls if path == "chat")
    assert chat["messages"] == [
        {
            "role": "user",
            "content": "Translate the following segment into English, without additional explanation.\n\n学校。",
        }
    ]
    assert chat["stream"] is False
    assert set(chat) == {"model", "messages", "stream", "options"}


@pytest.mark.parametrize(
    "info",
    [
        {"remote_host": "https://ollama.com", "capabilities": ["completion"]},
        {"remote_model": "cloud-alias", "capabilities": ["completion"]},
        {"capabilities": ["embedding"]},
    ],
)
def test_cloud_aliases_and_embedding_models_are_rejected_before_sending_text(monkeypatch, info):
    def request(path, body=None, timeout=5):
        assert path != "chat"
        return info if path == "show" else model_responses(path, body, timeout)

    monkeypatch.setattr(ollama, "request_json", request)
    with pytest.raises(ValueError):
        ollama.OllamaProvider("my-model").translate("学校")


@pytest.mark.parametrize(
    "value",
    [
        {"done": False, "message": {"content": "partial"}},
        {"done": True, "message": {"thinking": "hidden"}},
        {"done": True, "message": {"content": " "}},
    ],
)
def test_invalid_or_incomplete_chat_is_not_a_translation(monkeypatch, value):
    monkeypatch.setattr(
        ollama,
        "request_json",
        lambda path, body=None, timeout=5: (
            value if path == "chat" else model_responses(path, body, timeout)
        ),
    )
    with pytest.raises(RuntimeError, match="complete translation"):
        ollama.OllamaProvider("my-model").translate("学校")


def test_requests_disable_proxies_and_refuse_redirects(monkeypatch):
    handlers = []
    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return io.BytesIO(b"{}")

    def build(*args):
        handlers.extend(args)
        return Opener()

    monkeypatch.setattr("urllib.request.build_opener", build)
    assert ollama.request_json("tags") == {}
    assert calls[0][0].full_url == "http://127.0.0.1:11434/api/tags"
    assert handlers[0].proxies == {}
    with pytest.raises(ValueError, match="without redirects"):
        handlers[1].redirect_request(None, None, 302, None, None, "https://elsewhere/")


def test_pull_reports_progress_prevents_duplicates_and_does_not_select_model(monkeypatch):
    manager = ollama.OllamaDownloads()
    entered, proceed, finished = threading.Event(), threading.Event(), threading.Event()
    calls = []
    payload = b"\n".join(
        json.dumps(item).encode()
        for item in [
            {"status": "pulling weights", "total": 100, "completed": 50},
            {"status": "success"},
        ]
    )

    def open_request(path, body, timeout):
        calls.append((path, body))
        entered.set()
        assert proceed.wait(5)
        return io.BytesIO(payload)

    monkeypatch.setattr(ollama, "open_request", open_request)
    monkeypatch.setattr(ollama, "local_model", lambda name: {"name": name})
    original = manager._pull

    def pull(name):
        try:
            original(name)
        finally:
            finished.set()

    monkeypatch.setattr(manager, "_pull", pull)
    assert manager.start("my-model")["state"] == "downloading"
    assert entered.wait(5)
    manager.start("my-model")
    with pytest.raises(ValueError, match="current Ollama download"):
        manager.start("another")
    proceed.set()
    assert finished.wait(5)
    assert manager.status()["state"] == "ready"
    assert calls == [("pull", {"model": "my-model:latest", "stream": True})]


@pytest.mark.parametrize(
    "payload",
    [
        b'{"status":"pulling"}\n',
        b'{"error":"not found"}\n',
        b'{"status":"pulling","total":5,"completed":10}\n',
    ],
)
def test_failed_or_interrupted_pull_is_retryable(monkeypatch, payload):
    manager = ollama.OllamaDownloads()
    monkeypatch.setattr(ollama, "open_request", lambda *args, **kwargs: io.BytesIO(payload))
    manager._pull("my-model:latest")
    assert manager.status()["state"] == "error"


@pytest.mark.parametrize("revision", ["v1", "v2"])
def test_prompt_revision_does_not_reuse_old_conversational_answers(tmp_path, monkeypatch, revision):
    import sqlite3

    from app.translation import TranslationService

    source = "どういう役割の人が欲しいとかあるの？"
    calls = []

    def request(path, body=None, timeout=5):
        if path == "chat":
            calls.append(body)
            assert body["messages"][0]["content"].endswith("\n\n" + source)
            return {
                "done": True,
                "message": {"content": "What kind of role do you need someone for?"},
            }
        return model_responses(path, body, timeout)

    monkeypatch.setattr(ollama, "request_json", request)
    cache = tmp_path / "translations.sqlite3"
    with sqlite3.connect(cache) as db:
        db.execute(
            "CREATE TABLE translations (provider TEXT, source_text TEXT, translated_text TEXT, PRIMARY KEY(provider, source_text))"
        )
        db.execute(
            "INSERT INTO translations VALUES (?, ?, ?)",
            (
                "ollama-ja-en-" + revision + ":my-model:latest:" + DIGEST,
                source,
                "Yes, we need customer support.<�|hy_User｜>",
            ),
        )
    service = TranslationService(ollama.OllamaProvider("my-model"), cache)
    first = service.translate(source)
    assert first.cached is False
    assert first.translatedText == "What kind of role do you need someone for?"
    assert service.translate(source).cached is True
    assert len(calls) == 1


@pytest.mark.parametrize(
    "template", ["<｜hy_User｜>{{ .Content }}<｜hy_Assistant｜>", "{{ .Prompt }}"]
)
def test_hunyuan_turn_stops_prevent_invented_followup_without_overriding_other_models(
    monkeypatch, template
):
    chats = []

    def request(path, body=None, timeout=5):
        if path == "show":
            return {"capabilities": ["completion"], "template": template}
        if path == "chat":
            chats.append(body)
        return model_responses(path, body, timeout)

    monkeypatch.setattr(ollama, "request_json", request)
    ollama.OllamaProvider("my-model").translate("学校。")
    options = chats[0]["options"]
    if "<｜hy_User｜>" in template:
        assert options["stop"] == [
            "<｜hy_User｜>",
            "<｜hy_Assistant｜>",
            "<｜hy_place▁holder▁no▁2｜>",
            "<｜hy_place▁holder▁no▁8｜>",
        ]
    else:
        assert "stop" not in options


HY_MT2_METADATA = {
    "general.architecture": "hunyuan-dense",
    "tokenizer.ggml.bos_token_id": 127958,
    "tokenizer.ggml.eot_token_id": 127960,
    "tokenizer.ggml.seperator_token_id": 127962,
}


@pytest.mark.parametrize(
    "template", ["<｜hy_User｜>{{ .Content }}<｜hy_Assistant｜>", "custom", None]
)
def test_hy_mt2_uses_vocabulary_matched_raw_prompt_even_for_aliases(monkeypatch, template):
    calls = []

    def request(path, body=None, timeout=5):
        calls.append((path, body))
        if path == "show":
            return {
                "capabilities": ["completion"],
                "template": template,
                "model_info": HY_MT2_METADATA,
            }
        if path == "generate":
            return {"done": True, "done_reason": "stop", "response": "School."}
        assert path != "chat"
        return model_responses(path, body, timeout)

    monkeypatch.setattr(ollama, "request_json", request)
    assert ollama.OllamaProvider("my-model").translate("学校。") == "School."
    payload = next(body for path, body in calls if path == "generate")
    assert payload == {
        "model": "my-model:latest",
        "raw": True,
        "stream": False,
        "prompt": "<|startoftext|>Translate the following segment into English, without additional explanation.\n\n学校。<|extra_0|>",
        "options": {
            "temperature": 0,
            "num_predict": 512,
            "stop": ["<|eos|>", "<|extra_5|>", "<|startoftext|>"],
        },
    }


@pytest.mark.parametrize("key", list(HY_MT2_METADATA))
def test_other_vocabularies_do_not_receive_hy_mt2_prompt(monkeypatch, key):
    metadata = HY_MT2_METADATA | {key: "different"}

    def request(path, body=None, timeout=5):
        if path == "show":
            return {"capabilities": ["completion"], "model_info": metadata}
        assert path != "generate"
        return model_responses(path, body, timeout)

    monkeypatch.setattr(ollama, "request_json", request)
    assert ollama.OllamaProvider("my-model").translate("学校。") == "School."


@pytest.mark.parametrize("raw", [False, True])
@pytest.mark.parametrize(
    "output,reason",
    [
        ("School.<｜hy_User｜>Another turn", "stop"),
        ("School.<�|hy_User｜>Another turn", "stop"),
        ("School.< | hy_Assistant|>Repeat", "stop"),
        ("School.<|eos|>", "stop"),
        ("School.�", "stop"),
        ("School", "length"),
    ],
)
def test_malformed_or_truncated_output_is_not_returned_or_cached(
    tmp_path, monkeypatch, raw, output, reason
):
    import sqlite3

    from app.translation import TranslationService

    def request(path, body=None, timeout=5):
        if path == "show" and raw:
            return {"capabilities": ["completion"], "model_info": HY_MT2_METADATA}
        if path in ("generate", "chat"):
            return {
                "done": True,
                "done_reason": reason,
                "response": output,
                "message": {"content": output},
            }
        return model_responses(path, body, timeout)

    monkeypatch.setattr(ollama, "request_json", request)
    cache = tmp_path / "cache.sqlite3"
    service = TranslationService(ollama.OllamaProvider("my-model"), cache)
    with pytest.raises(RuntimeError, match="complete translation|malformed translation"):
        service.translate("学校。")
    with sqlite3.connect(cache) as db:
        assert db.execute("SELECT COUNT(*) FROM translations").fetchone()[0] == 0
