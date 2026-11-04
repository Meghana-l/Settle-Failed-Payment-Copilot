"""
Drafts the message a customer sends to whoever has to act.

The model only rewrites facts it is given. It never decides why a payment
failed and never triggers a retry. If no API key is set, or the call fails,
we fall back to a fixed template so the feature still works.
"""
import os

MODEL = os.getenv("SETTLE_MODEL", "claude-haiku-5-5")

# What we ask the recipient to do, written to them (not to the customer).
ASKS = {
    "R02": "send us your current bank details",
    "R03": "confirm your routing and account number",
    "R16": "let us know if there's another account we should use",
    "R20": "send us details for a checking account",
    "R08": "check whether a stop payment was placed and lift it if it was a mistake",
    "R29": "add our banking platform's ACH company ID to the allowed list on our account",
    "FRAUD": "confirm whether you made this charge",
}


def recipient_for(p: dict):
    actor = p["actor"]
    if actor == "Your vendor":
        return p["counterparty"]
    if actor == "Your other bank":
        return "your other bank"
    if actor == "Your cardholder":
        return p.get("cardholder", "the cardholder")
    return None  # the customer fixes it themselves; nobody to message


def build_prompt(p: dict, company: str, to: str) -> str:
    return (
        f"Write a short, friendly email from {company} (a startup) to {to} about a failed payment.\n"
        "Use ONLY these facts. Do not add any others:\n"
        f"- Amount: ${p['amount']:,.2f}\n"
        f"- Payment type: {p['rail']}\n"
        f"- What happened: {p['plain']}\n"
        f"- What we need from them: {' '.join(p['steps'])}\n"
        "Rules: under 110 words, plain language, no blame, no legal claims, "
        f"no ACH codes, sign off as \"{company}\". Return only the email body."
    )


def template(p: dict, company: str, to: str) -> str:
    greeting = "Hi," if to.startswith("your") else f"Hi {to},"
    ask = ASKS.get(p["code"], "help us sort this out")
    return (f"{greeting}\n\nA ${p['amount']:,.2f} payment from {company} didn't go through. {p['plain']}\n\n"
            f"Could you {ask}?\n\n"
            f"Once that's sorted we'll send it again right away.\n\nThanks,\n{company}")


def draft(p: dict, company: str) -> dict:
    to = recipient_for(p)
    if to is None:
        return {"text": "", "source": "none", "note": "You can fix this one yourself, so there's nobody to message."}
    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"text": template(p, company, to), "source": "template",
                "note": "No API key set, so this is the template."}
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=MODEL, max_tokens=400,
            messages=[{"role": "user", "content": build_prompt(p, company, to)}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return {"text": text, "source": "ai", "note": "Draft ready. Review it before sending."}
    except Exception:
        return {"text": template(p, company, to), "source": "template",
                "note": "Couldn't reach the model, so this is the template."}
