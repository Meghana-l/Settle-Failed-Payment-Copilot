# Settle: Failed-Payment Copilot

Money moves, cards get declined, and payments either settle or fail. **Settle focuses on the moment a payment fails, when a bank transfer comes back or a card is declined, and turns it into a plain-English explanation plus a one-click fix.**

In the US, most transfers between bank accounts travel over **ACH**, the network banks use to move money between accounts. When an ACH payment fails, the bank sends back only a short **return code**, like R03. With Settle, a founder sees this instead:

> "Your $8,400 payment to Northwind Studio came back because their bank couldn't find an account with that number (ACH return code R03). Ask them to confirm their details. Here's a message ready to send."

Finance teams also get a view of which payments are at risk of failing **before** they go out.

**Live demo:** _add your Vercel link here_

---

## Why it matters

Most founders don't know what return codes mean, who is supposed to fix them, or whether trying again will make things worse. So they contact support and wait, and the vendor waits too. Every failed payment is a moment where a customer decides whether they trust their bank with their money.

## What Settle does

When a payment fails, Settle shows four things:

1. **What happened, in plain English.** Instead of "R03," it says: *"Northwind Studio's bank couldn't find an account with the number you used. Your money is back in your account."*
2. **Who needs to act.** You, your vendor, your other bank, or the employee holding the card.
3. **What to do next.** Short steps, plus a button to fix it, such as editing the vendor's bank details.
4. **A message ready to send.** If someone else has to act, AI drafts the email to them for you to review.

Settle also checks payments **before** they go out. It warns you if a vendor's bank details changed in the last week (a common trick scammers use) or if a scheduled batch of payments is bigger than your balance.

## What I found

Settle covers 13 common ways a payment can fail. Grouping them showed two things that shaped the product:

- **7 of the 13 failures need someone other than you to fix them.** Explaining the problem isn't enough, so Settle also drafts the message to the person who can fix it.
- **9 of the 13 will fail again if you just try again without changing anything.** So Settle blocks the "send again" button until the cause is fixed, which saves days of waiting on a payment that was never going to work.

## How AI is used, and where it isn't

The explanation for every failure comes from a fixed list I wrote and checked, not from AI. A wrong explanation about someone's money is worse than no explanation.

AI is used only to write the message to the vendor or bank, using the facts from that list. A person always reviews it before sending. AI never moves money or retries a payment.

## How I'd measure success

I defined these before building:

- **Main goal:** less time between a payment failing and the customer fixing it
- **Fewer repeat failures:** payments that fail again after being retried
- **Fewer support tickets** about failed payments
- **Safety check:** customers shouldn't start ignoring the fraud warnings, so they need to stay rare and accurate

## Failures Settle covers

**Payments you send to a vendor**
- The vendor's account is closed (code R02)
- The vendor's bank can't find the account (code R03)
- The account number isn't valid (code R04)
- The vendor's account is frozen (code R16)
- The account can't accept transfers, such as some savings accounts (code R20)

**Money you move in from your other bank**
- Your other bank didn't have enough money (code R01). The rules allow at most two retries within 180 days, and Settle enforces that.
- Someone placed a stop on the transfer (code R08)
- Your other bank blocked the transfer because it wasn't told to allow it (code R29)

**Company card payments**
- The card hit its spending limit
- International charges are turned off
- The charge was paused as possible fraud

**Checks before a payment goes out**
- The vendor's bank details changed in the last 7 days
- A scheduled batch of payments is bigger than your expected balance

## Built with

Python and FastAPI for the backend, plain HTML and JavaScript for the interface, the Claude API for message drafts, and Vercel for hosting.

---

Concept prototype by **Meghana Lakshminarayana Swamy**. Not affiliated with any bank. All companies, people, and amounts are made up. Return codes follow the rules of NACHA, the organization that runs the ACH network.
