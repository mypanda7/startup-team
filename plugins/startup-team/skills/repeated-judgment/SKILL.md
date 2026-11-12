---
name: repeated-judgment
description: Method for a judgement that REPEATS over many items, such as "is this card the same idea as any of these 900?", "does this error cluster match one already triaged?" or "does this draft break any of these rules?". One small, literal question per item, answered by a cheap model or classifier the project has set up, so you read far fewer items yourself. The cheap answers only FIND candidates; you verify every hit. Advisory only.
---

# Repeated judgement: a finder, not a judge

When the same yes/no, pick-one or score question has to be asked of hundreds of items, do not
read them all with an expensive model and do not ask one giant question. Ask a cheap model one
small question per item, then check the hits yourself.

Use whatever cheap model or classifier the project's CLAUDE.md names for this, through the
command it names. If it names none, run the same method with the team's cheapest model
(`skill-sub`) in batches, or fall back to search plus reading. The rules below hold either way.

**The cheap pass FINDS. You VERIFY every hit against the source. Nothing is sent, merged,
blocked, ticked or deleted on a cheap answer.** A probability describes many answers; it never
authorizes one action. Expect a large share of top hits to be wrong: a cheap pass reads
literally, cannot see that something is stale, and cannot see a fact that lives in another file.
Do not ask it to generate, count, do arithmetic or compare dates.

## Rules
1. **Key every item; never refer to an item by position.** Give each item its own question, or
   its own id inside the text, and join the answers back by id. "Is item 37 ..." gets a
   noticeable share of items wrong. Refuse to work from a positional list.
2. **One question per item beats one big question.** Accuracy falls as the context fills with
   unrelated text. Keep each question's context far below the model's limit.
3. **Write literal, concrete questions.** Describe a situation ("the endpoint reads a record by
   an id from the request without checking it belongs to the caller"), not a degree ("is this
   insecure?"). A vague question comes back as a coin flip.
4. **Give a pick-one question an explicit "none of these" option**, or the model must pick
   something. Give a score question a written rubric for each level.
5. **Decide what may leave the machine before anything does.** Only the classes of text the owner
   has signed off for an outside model. Never personal data, a reporter's identity, a support
   message body, a secret, or anything read from a live database. If the project has a redaction
   step, choose its setting on purpose, look at what would be sent first, and when unsure use
   the strictest one. No setting makes the forbidden classes acceptable.
6. **Call it only the way the project says.** The project's command is where its refusals,
   redaction, version pin and cost cap live. Never go around it with a direct call.
7. **Fail open, and say so.** If the cheap model is unavailable, refuses, or its budget is spent,
   do exactly what you would have done without it and tell the owner in one line. A malformed
   call is your own mistake: fix the call.
8. **Report each hit with its verdict**: "suggested (p=0.87): verified | rejected | stale", with
   `file:line`. Also say what a plain text search would have caught, so the value added stays
   visible.
9. **Replay a threshold before relying on it.** Run it over past decisions whose right answer is
   known, record the agreement and every miss in the project's notes, and note the model version.
   A new version means a new replay.

## Procedure
1. State the judgement as one question with a fixed answer type: yes/no, pick one, or a score.
2. Build the item list with stable ids. Narrow it first with a plain search where that is safe.
3. Run the cheap pass, one question per item, and join the answers by id.
4. Sort by confidence. Read and verify every hit above your threshold, and a sample below it to
   see what the pass missed.
5. Report the verified hits, the rejected ones, the sample result, and anything you could not
   check. Any action that follows goes through the team's normal chain.
