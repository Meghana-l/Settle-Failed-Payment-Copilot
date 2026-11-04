"""Settle: API and frontend, served as one FastAPI app (deploys to Vercel as-is)."""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from settle.codes import explain, REASONS, MAX_REPRESENTMENTS
from settle.drafts import draft

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / "data" / "sample_payments.json").read_text())
COMPANY = DATA["company"]
PAYMENTS = {p["id"]: dict(p) for p in DATA["payments"]}  # in-memory demo state

app = FastAPI(title="Settle", version="1.0.0")


def _get(pid: str) -> dict:
    if pid not in PAYMENTS:
        raise HTTPException(404, "Payment not found")
    return PAYMENTS[pid]


@app.get("/api/payments")
def list_payments():
    items = [explain(p) for p in PAYMENTS.values()]
    failed = [i for i in items if i["kind"] != "preflight"]
    return {
        "company": COMPANY,
        "summary": {
            "failed": len(failed),
            "you_can_fix": sum(i["actor"] == "You" or i["actor"].startswith("You (") for i in failed),
            "flagged_before_sending": len(items) - len(failed),
        },
        "payments": items,
    }


@app.get("/api/reasons")
def list_reasons():
    """The reason library, used by the Insights view."""
    return [{"code": r.code, "kind": r.kind, "title": r.title, "actor": r.actor,
             "resend_blocked": r.resend_blocked} for r in REASONS.values()]


@app.post("/api/payments/{pid}/retry")
def retry(pid: str):
    p = _get(pid)
    e = explain(p)
    if e["fix"] != "retry":
        raise HTTPException(409, "This payment can't be retried as-is.")
    if p.get("retries", 0) >= MAX_REPRESENTMENTS:
        raise HTTPException(409, "No retries left for this payment.")
    p["retries"] = p.get("retries", 0) + 1
    return explain(p)


@app.post("/api/payments/{pid}/draft")
def draft_message(pid: str):
    return draft(explain(_get(pid)), COMPANY)


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")

