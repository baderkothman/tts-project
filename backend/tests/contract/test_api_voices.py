"""Provider/voice/locale listing endpoints (FR-023)."""


def test_list_voices_all_providers(client):
    r = client.get("/api/voices")
    assert r.status_code == 200
    voices = r.json()
    assert len(voices) >= 32  # at least edge's 32


def test_list_voices_filtered_by_provider(client):
    r = client.get("/api/voices", params={"provider": "edge"})
    assert r.status_code == 200
    voices = r.json()
    assert len(voices) == 32
    assert all(v["provider"] == "edge" for v in voices)


def test_list_voices_filtered_by_locale(client):
    r = client.get("/api/voices", params={"locale": "ar-EG"})
    assert r.status_code == 200
    voices = r.json()
    assert all(v["locale"] == "ar-EG" for v in voices)
    assert len(voices) >= 2  # at least edge's female+male for ar-EG


def test_list_locales(client):
    r = client.get("/api/locales")
    assert r.status_code == 200
    body = r.json()
    assert len(body["locales"]) == 16
    assert "ar-SA" in body["locales"]
    assert body["display_names"]["ar-SA"] == "Saudi Arabia"
