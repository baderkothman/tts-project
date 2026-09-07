"""User text and audio are never logged (FR-040, Constitution VII).

Added by /speckit-analyze finding E1: FR-040 is a constitution MUST that had
zero task coverage before this test.
"""

import logging


def test_synthesis_does_not_log_request_text(client, caplog):
    secret_text = "هذا نص سري لا يجب أن يظهر في أي سجل XYZUNIQUE12345"
    with caplog.at_level(logging.DEBUG):
        client.post("/api/preview", json={"text": secret_text})
    assert "XYZUNIQUE12345" not in caplog.text


def test_tts_endpoint_does_not_log_request_text(client, caplog):
    secret_text = "نص آخر سري QQRANDOMTOKEN98765"
    with caplog.at_level(logging.DEBUG):
        client.post("/api/tts", json={"text": secret_text})
    assert "QQRANDOMTOKEN98765" not in caplog.text
