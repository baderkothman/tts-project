"""Benchmark and sample listing endpoints (FR-035, FR-038)."""


def test_list_samples(client):
    r = client.get("/api/samples")
    assert r.status_code == 200
    samples = r.json()
    assert len(samples) == 11
    categories = {s["category"] for s in samples}
    assert "numbers" in categories
    assert "dates" in categories
    assert "pronunciation" in categories


def test_benchmark_unknown_provider_returns_404(client):
    r = client.post("/api/benchmark", json={"provider": "nonexistent"})
    assert r.status_code == 404
