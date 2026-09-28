import gzip

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<JMdict>
<entry><ent_seq>1</ent_seq><k_ele><keb>今日</keb><ke_pri>ichi1</ke_pri></k_ele>
<r_ele><reb>きょう</reb><re_pri>ichi1</re_pri></r_ele>
<r_ele><reb>こんにち</reb></r_ele>
<sense><gloss>today</gloss></sense>
<sense><stagr>こんにち</stagr><gloss>these days</gloss></sense></entry>
<entry><ent_seq>2</ent_seq><k_ele><keb>待つ</keb></k_ele>
<r_ele><reb>まつ</reb></r_ele><sense><gloss>to wait</gloss></sense></entry>
<entry><ent_seq>3</ent_seq><k_ele><keb>生</keb></k_ele>
<r_ele><reb>なま</reb></r_ele><sense><gloss>raw</gloss></sense></entry>
<entry><ent_seq>4</ent_seq><k_ele><keb>生</keb></k_ele>
<r_ele><reb>せい</reb></r_ele><sense><gloss>life</gloss></sense></entry>
</JMdict>""".encode()


def _install(monkeypatch, tmp_path, content=FIXTURE):
    source = tmp_path / "JMdict_e.gz"
    with gzip.open(source, "wb") as output:
        output.write(content)
    index = tmp_path / "index.sqlite3"
    monkeypatch.setenv("YOMIMADO_JMDICT", str(source))
    monkeypatch.setenv("YOMIMADO_JMDICT_INDEX", str(index))
    return source, index


def test_word_lookup_uses_combined_meaning_and_reading(monkeypatch, tmp_path) -> None:
    _, index = _install(monkeypatch, tmp_path)
    response = client.post(
        "/api/v1/word",
        json={"surface": "今日", "dictionaryForm": "今日", "reading": "キョウ"},
    )
    assert response.status_code == 200
    entry = response.json()["entries"][0]
    assert entry["expression"] == "今日"
    assert entry["reading"] == "きょう"
    assert entry["senses"] == [{"glosses": ["today"]}]
    assert entry["readingMatch"] is True
    assert index.is_file()


def test_dictionary_form_fallback_and_ambiguous_readings(monkeypatch, tmp_path) -> None:
    _install(monkeypatch, tmp_path)
    inflected = client.post(
        "/api/v1/word",
        json={"surface": "待って", "dictionaryForm": "待つ", "reading": "マッテ"},
    ).json()["entries"]
    assert inflected[0]["match"] == "dictionaryForm"
    assert inflected[0]["senses"] == [{"glosses": ["to wait"]}]

    ambiguous = client.post(
        "/api/v1/word",
        json={"surface": "生", "dictionaryForm": "生", "reading": "セイ"},
    ).json()["entries"]
    assert [item["reading"] for item in ambiguous] == ["せい", "なま"]
    assert ambiguous[0]["readingMatch"] is True
    assert ambiguous[1]["readingMatch"] is False


def test_missing_and_changed_dictionary(monkeypatch, tmp_path) -> None:
    source, _ = _install(monkeypatch, tmp_path)
    assert client.post(
        "/api/v1/word",
        json={"surface": "今日", "dictionaryForm": "今日", "reading": "キョウ"},
    ).json()["entries"]
    with gzip.open(source, "wb") as output:
        output.write(FIXTURE.replace(b"today", b"this day"))
    updated = client.post(
        "/api/v1/word",
        json={"surface": "今日", "dictionaryForm": "今日", "reading": "キョウ"},
    ).json()["entries"]
    assert updated[0]["senses"] == [{"glosses": ["this day"]}]

    monkeypatch.setenv("YOMIMADO_JMDICT", str(tmp_path / "missing.gz"))
    missing = client.post(
        "/api/v1/word",
        json={"surface": "今日", "dictionaryForm": "今日", "reading": "キョウ"},
    )
    assert missing.status_code == 503
    assert "JMdict is not installed" in missing.json()["detail"]
    missing_examples = client.post("/api/v1/kanji/examples", json={"character": "今"})
    assert missing_examples.status_code == 503


def test_kanji_examples_are_common_compounds_not_the_selected_word(monkeypatch, tmp_path) -> None:
    examples = """
<entry><ent_seq>5</ent_seq><k_ele><keb>今度</keb><ke_pri>nf03</ke_pri></k_ele>
<r_ele><reb>こんど</reb></r_ele><sense><gloss>this time</gloss></sense></entry>
<entry><ent_seq>6</ent_seq><k_ele><keb>今月</keb><ke_pri>nf05</ke_pri></k_ele>
<r_ele><reb>こんげつ</reb></r_ele><sense><gloss>this month</gloss></sense></entry>
<entry><ent_seq>7</ent_seq><k_ele><keb>今回</keb><ke_pri>nf01</ke_pri></k_ele>
<r_ele><reb>こんかい</reb></r_ele><sense><gloss>this time</gloss></sense></entry>
<entry><ent_seq>8</ent_seq><k_ele><keb>今朝</keb><ke_pri>nf10</ke_pri></k_ele>
<r_ele><reb>けさ</reb></r_ele><sense><gloss>this morning</gloss></sense></entry>
<entry><ent_seq>9</ent_seq><k_ele><keb>今すぐ</keb><ke_pri>nf01</ke_pri></k_ele>
<r_ele><reb>いますぐ</reb></r_ele><sense><gloss>right now</gloss></sense></entry>
""".encode()
    _install(monkeypatch, tmp_path, FIXTURE.replace(b"</JMdict>", examples + b"</JMdict>"))
    response = client.post(
        "/api/v1/kanji/examples", json={"character": "今", "excludeWord": "今度"}
    )
    assert response.status_code == 200
    assert response.json()["examples"] == [
        {"expression": "今回", "reading": "こんかい", "meanings": ["this time"]},
        {"expression": "今月", "reading": "こんげつ", "meanings": ["this month"]},
        {"expression": "今朝", "reading": "けさ", "meanings": ["this morning"]},
    ]
    invalid = client.post("/api/v1/kanji/examples", json={"character": "?"})
    assert invalid.status_code == 422
