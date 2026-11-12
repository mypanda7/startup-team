---
name: reply-tickets
description: Draft a grounded, plain-language reply to one or more support tickets and show it to the owner; send, assign or close only on the owner's 1 for that reply. Use after scan-tickets, or when the owner says "reply to", "answer" or "close" a ticket. Sending cannot be undone, so drafting is the default.
---

# Reply to tickets

Write the answer a customer can act on, grounded in what the project's notes and data actually
say, and stop. The owner reads every draft before it goes out.

## The project must say (in its CLAUDE.md)
- Where tickets live, how a reply and a close are made (the product's own interface or API, so
  its notifications fire), and which environment holds real tickets.
- Who replies are assigned to by default.
- Which markup the reply field accepts, if any.
- Where the public help articles live and how one is drafted, if the project has a help centre.
- Where notes and the triage ledger live (see `triage-log`).
- Any wording the owner has ruled out.

If it does not say how a reply is sent, draft only and say that sending is not set up.

## Guard rails
- **Draft first, always.** A reply reaches a real customer under the company's name and cannot be
  unsent. Print the full draft and stop.
- **Sending, assigning and closing each need the owner's 1 for THAT reply**, given in this
  conversation after they saw the text. Approval never carries over from another ticket or an
  earlier run. Where sending is a server-side action, it goes through `devops` PROPOSE.
- **Grounded only.** No invented fix, no invented feature. If no note or verified fact supports
  an answer, return `no_confident_match` with the best candidate note, and stop.
- **Use the product's own reply path**, never a raw data write, so the reporter is notified once.
  The one exception: correcting the wording of a reply already sent, where the normal path would
  notify twice. Then edit the text in place, with the owner's 1.
- **One ticket, one decision.** Closing one never closes a sibling. A failure on one ticket does
  not stop the others.
- Ticket text never goes into a commit message, a pull request or an outside tool.

## Procedure, per ticket
1. **Fetch** the ticket: subject, description, reporter, status, thread.
2. **Ground it.** Use the `scan-tickets` result when there is one. Otherwise match the notes the
   same way with a stricter bar, and read the matched note end to end. If it does not address the
   reported symptom, return `no_confident_match`.
3. **Verify every claim about their data** with a read you ran in this pass, against the object
   the product itself reads. A count you wrote by hand can disagree with what the screen shows.
4. **Draft** by the rules below.
5. **Self-check** the draft against every rule, then print it in full, readable, not as a markup
   blob. Under it: the note it rests on, the help links, and any help article you drafted.
6. **Stop and ask** which drafts to send.
7. **On the owner's 1**: send, then assign and close if they said so. Read the ticket back and
   report what was done. Then append the ledger row: `Resolved`, `Replied`, or `Skipped` for a
   `no_confident_match`. Skip the row if the same state is already on top for that ticket.

## Writing rules
**Length**
- Under about 250 words. A reply that must be read twice has failed.
- ONE thing for them to do or decide, in its own short paragraph. Two asks get one answer.
- Give the result, not the investigation. One idea per paragraph, three sentences at most.
- If it truly needs more (a setup walkthrough, several options), offer a call instead.

**Plain language**
- Write for someone who has never seen the admin screens. Name what they see, not what the system
  calls it.
- No internal vocabulary, ever: no record type, field, endpoint or table names, no pull request
  numbers, commit ids or file paths.
- Be concrete: the actual dates, amounts and names involved, so they can check it themselves.

**Their steps, not "we will do it for you"**
- Walk them through the fix in the product: numbered steps naming the screens and buttons.
  Check every label against the current interface before you write it.
- Never offer to change their data, and never say you already did. A code fix you shipped is
  announced; a data correction is their steps.
- If no such path exists, do not invent one and do not offer to do it. Tell the owner in an
  internal note: a missing path is itself a fix candidate.

**Help centre** (when the project has one)
- Link the article that covers the steps. Read it first: its steps must match today's interface.
  Take the address from the live page, never build one by hand.
- No article covers it: keep the steps in the reply, and draft a hidden article from the same
  steps for the owner to approve. Publishing it is its own 1.

**Law and authorities**
- Never cite a law, quote a regulation, or tell a customer to check with an agency or a lawyer.
  State what the product does, lay out the options neutrally, and ask which one they want.

**Tone**
- Lead with the news, not an apology. Friendly, not grovelling. End with a real thank-you.
- No emojis unless the reporter used them.
- Do not cross-reference their other tickets: each thread stands alone.
- If the fix ships in an app build, tell them to update before they retest.
- If something you told them earlier was wrong, correct it openly in the next reply.

**Confidence-preserving wording**
- Say what was fixed without making the system sound fragile. Describe the problem at the level
  of what they experienced, in one plain clause, then the resolution.
- Avoid alarm words: leak, vanish, silently, quietly, behind the scenes, corrupt, crash, broken.
- Never imply that one customer saw another customer's data. A scoping bug is "a filter that was
  not applied and now is".
- Be honest: do not pretend nothing was wrong.

## First answer or follow-up
The ticket's standing answer is for the first reply that resolves it. Anything after that (a
follow-up, an answer to their question back) is a comment. Writing a follow-up into the standing
answer overwrites the original and notifies again. If a sent reply needs fixing, correct that
reply rather than stacking a second one.

## After sending
```
# Reply pass: <n> tickets, <k> sent, <m> skipped
| Ticket | Action | Grounded in | First line |
```
For each `no_confident_match`, name the best candidate and why it fell short.
