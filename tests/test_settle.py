from fastapi.testclient import TestClient

import app as settle_app
from settle.codes import REASONS, explain
from settle.drafts import template, build_prompt

client = TestClient(settle_app.app)


def test_every_reason_is_complete():
    for code, r in REASONS.items():
        assert r.title and r.plain and r.actor, code
        assert len(r.steps) >= 2, code
        assert "{who}" in r.plain or r.kind == "preflight", code


def test_wrong_account_details_cannot_be_resent_as_is():
    for code in ("R02", "R03", "R04", "R20"):
        assert REASONS[code].resend_blocked


def test_r01_retry_limit_is_enforced():
    pid = "p5"
    settle_app.PAYMENTS[pid]["retries"] = 1
    assert client.post(f"/api/payments/{pid}/retry").json()["retries_left"] == 0
    assert client.post(f"/api/payments/{pid}/retry").status_code == 409


def test_non_retryable_payment_rejects_retry():
    assert client.post("/api/payments/p1/retry").status_code == 409


def test_explanations_never_show_raw_codes():
    for p in settle_app.PAYMENTS.values():
        e = explain(p)
        assert e["code"] not in e["plain"]


def test_draft_uses_only_given_facts():
    e = explain(settle_app.PAYMENTS["p1"])
    prompt = build_prompt(e, "Lumen Labs", "Northwind Studio")
    assert "R03" not in prompt and "Use ONLY these facts" in prompt
    assert "R03" not in template(e, "Lumen Labs", "Northwind Studio")


def test_draft_falls_back_to_template_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/api/payments/p1/draft").json()
    assert r["source"] == "template" and "Northwind Studio" in r["text"]


def test_summary_counts():
    s = client.get("/api/payments").json()["summary"]
    assert s == {"failed": 7, "you_can_fix": 3, "flagged_before_sending": 2}


def test_template_asks_the_recipient_directly():
    e = explain(settle_app.PAYMENTS["p1"])
    assert "Could you confirm your routing and account number?" in template(e, "Lumen Labs", "Northwind Studio")


def test_reasons_endpoint_covers_library():
    assert len(client.get("/api/reasons").json()) == len(REASONS) == 13
