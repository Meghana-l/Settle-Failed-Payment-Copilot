"""
Reason library for failed and at-risk payments.

Every explanation a customer sees comes from this file, never from a model.
A wrong explanation about money is worse than a slow one, so facts are
deterministic and reviewed; AI is only used to draft messages (see drafts.py).

ACH return code meanings follow NACHA definitions. Card decline reasons are
simplified for the prototype.
"""
from dataclasses import dataclass, field

MAX_REPRESENTMENTS = 2  # NACHA: a returned R01/R09 entry can be re-presented at most twice within 180 days


@dataclass(frozen=True)
class Reason:
    code: str
    kind: str            # "ach_return" | "card_decline" | "preflight"
    title: str
    plain: str           # uses {who}
    actor: str           # who has to act
    steps: list = field(default_factory=list)
    retry_note: str = ""
    resend_blocked: bool = True   # True = resending as-is will fail again
    fix: str = "message"          # edit | retry | limit | confirm | message


REASONS = {
    # ---- ACH returns on payouts (ACH credits you send) ----
    "R02": Reason("R02", "ach_return", "Account closed",
        "{who}'s bank says the account you paid has been closed.",
        "Your vendor",
        ["Ask the vendor for their current bank details.",
         "Confirm the new details by phone using a number you already have.",
         "Edit the payee and resend."],
        "Don't resend to the same account. It will fail again.", True, "edit"),
    "R03": Reason("R03", "ach_return", "No account found",
        "{who}'s bank couldn't find an account with the number you used.",
        "Your vendor",
        ["Ask the vendor to confirm their routing and account number.",
         "Edit the payee with the corrected number.",
         "Resend the payment."],
        "Resending with the same details will fail again, so it's locked until the number changes.", True, "edit"),
    "R04": Reason("R04", "ach_return", "Invalid account number",
        "The account number for {who} isn't in a valid format for that bank.",
        "You",
        ["Check the payee details for a typo or missing digit.",
         "Compare against the vendor's invoice or payment details.",
         "Correct it and resend."],
        "Locked until the account number is edited.", True, "edit"),
    "R16": Reason("R16", "ach_return", "Account frozen",
        "{who}'s bank has frozen the receiving account, so it can't accept money right now.",
        "Your vendor",
        ["Let the vendor know the payment was returned.",
         "Ask whether they have another account to use.",
         "Resend once they confirm."],
        "Wait for the vendor before resending.", True, "message"),
    "R20": Reason("R20", "ach_return", "Account can't receive this payment",
        "{who} gave you an account that doesn't accept transfers, like a savings account with limits.",
        "Your vendor",
        ["Ask the vendor for a checking account instead.",
         "Update the payee.",
         "Resend."],
        "Locked until the payee details change.", True, "edit"),
    # ---- ACH returns on funding pulls (ACH debits from your other bank) ----
    "R01": Reason("R01", "ach_return", "Not enough money in your other bank",
        "We tried to move money in from {who}, but that account didn't have enough funds.",
        "You",
        ["Top up the external account.",
         "Retry the transfer from here."],
        "A returned pull can be re-presented at most twice within 180 days.", False, "retry"),
    "R08": Reason("R08", "ach_return", "Payment stopped",
        "Someone placed a stop on this transfer at {who}.",
        "Your other bank",
        ["Check with your other bank whether a stop payment was placed.",
         "Remove it if it was a mistake.",
         "Start a new transfer."],
        "Start a new transfer once the stop is lifted.", True, "message"),
    "R29": Reason("R29", "ach_return", "Your other bank blocked the pull",
        "{who} blocked this transfer because it hasn't been told to allow pulls from your banking platform.",
        "Your other bank",
        ["Ask your other bank to add the platform's ACH company ID to your allowed list (an ACH debit filter).",
         "Wait for them to confirm.",
         "Retry the transfer."],
        "Retrying before the bank updates its filter will fail the same way.", True, "message"),
    # ---- Card declines ----
    "LIMIT": Reason("LIMIT", "card_decline", "Card spend limit reached",
        "This card hit its monthly limit, so the charge at {who} was declined.",
        "You (card admin)",
        ["Raise the card's limit, or approve a one-time increase.",
         "Ask the cardholder to try the charge again."],
        "The merchant will usually let the cardholder retry right away.", False, "limit"),
    "INTL": Reason("INTL", "card_decline", "International charges are off",
        "{who} charged from outside the US, and this card only allows domestic spend.",
        "You (card admin)",
        ["Turn on international charges for this card, or for this trip only.",
         "Ask the cardholder to retry."],
        "Safe to retry once the setting changes.", False, "limit"),
    "FRAUD": Reason("FRAUD", "card_decline", "Held as possible fraud",
        "The charge at {who} looked unusual for this card, so it was paused.",
        "Your cardholder",
        ["Ask the cardholder if they made this charge.",
         "If yes, confirm it in the app and retry.",
         "If not, freeze the card and contact support."],
        "Don't retry until the cardholder confirms the charge.", True, "message"),
    # ---- Pre-flight checks on scheduled payments ----
    "BDCHANGE": Reason("BDCHANGE", "preflight", "Bank details changed recently",
        "{who}'s bank details were updated in the last 7 days. Fraudsters often send \"new\" details by email right before a payment.",
        "You",
        ["Call the vendor on a number you already had, not one from the email.",
         "Confirm the new routing and account number.",
         "Approve the payment, or put it on hold."],
        "This payment is on hold until you confirm.", True, "confirm"),
    "BALANCE": Reason("BALANCE", "preflight", "Batch is bigger than your balance",
        "The scheduled payout batch is more than your expected balance on that day.",
        "You",
        ["Move funds in before the cutoff the day before.",
         "Or remove lower-priority payments from the batch."],
        "Nothing has failed yet. Fixing it now avoids a return.", False, "message"),
}


def explain(payment: dict) -> dict:
    """Attach the customer-facing explanation to a payment record."""
    reason = REASONS[payment["code"]]
    who = payment["counterparty"]
    retry_note = reason.retry_note
    retries_left = None
    if reason.fix == "retry":
        retries_left = max(0, MAX_REPRESENTMENTS - payment.get("retries", 0))
        retry_note = (f"You can retry this {retries_left} more time{'s' if retries_left != 1 else ''}. "
                      + reason.retry_note) if retries_left else "No retries left. Contact support to move funds another way."
    if reason.kind == "ach_return":
        money_note = ("No money left your account." if payment["rail"].endswith("pull")
                      else "The money is back in your account.")
        status_note = f"ACH return code {reason.code}. {money_note}"
    elif reason.kind == "card_decline":
        status_note = "Card decline. No money was charged."
    else:
        status_note = "Pre-flight check. Nothing has been sent."
    return {
        **payment,
        "title": reason.title,
        "plain": reason.plain.format(who=who),
        "actor": reason.actor,
        "steps": reason.steps,
        "retry_note": retry_note,
        "retries_left": retries_left,
        "resend_blocked": reason.resend_blocked,
        "fix": reason.fix,
        "kind": reason.kind,
        "status_note": status_note,
    }
