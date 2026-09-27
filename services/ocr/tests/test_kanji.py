import gzip

from fastapi.testclient import TestClient

from app.dictionary.kanjidic import _load
from app.main import app

client = TestClient(app)
FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<kanjidic2><header><file_version>4</file_version></header>
<character><literal>学</literal><reading_meaning><rmgroup>
<reading r_type="ja_on">ガク</reading><reading r_type="ja_kun">まな.ぶ</reading>
<meaning>study</meaning><meaning m_lang="fr">etude</meaning>
</rmgroup></reading_meaning></character>
<character><literal>校</literal><reading_meaning><rmgroup>
<reading r_type="ja_on">コウ</reading><meaning>school</meaning>
</rmgroup></reading_meaning></character>
</kanjidic2>""".encode()


def test_local_kanjidic_lookup(monkeypatch, tmp_path) -> None:
    path = tmp_path / "kanjidic2.xml.gz"
    with gzip.open(path, "wb") as output:
        output.write(FIXTURE)
    monkeypatch.setenv("YOMIMADO_KANJIDIC2", str(path))
    _load.cache_clear()

    response = client.post("/api/v1/kanji", json={"character": "学"})
    assert response.status_code == 200
    assert response.json() == {
        "character": "学",
        "onReadings": ["ガク"],
        "kunReadings": ["まな.ぶ"],
        "meanings": ["study"],
    }
    assert client.post("/api/v1/kanji", json={"character": "未"}).status_code == 404
    assert client.post("/api/v1/kanji", json={"character": "学校"}).status_code == 422


def test_missing_dictionary_reports_setup_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("YOMIMADO_KANJIDIC2", str(tmp_path / "missing.xml.gz"))
    _load.cache_clear()
    response = client.post("/api/v1/kanji", json={"character": "学"})
    assert response.status_code == 503
    assert "KANJIDIC2 is not installed" in response.json()["detail"]
