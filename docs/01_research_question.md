# Pulse — Research Question (Restated)

A football match is not a static object — it's a process that unfolds minute by minute, and the "right" read of the game changes as it goes. Pulse asks whether a language model can be dropped into the middle of that process and reason about it the way a knowledgeable viewer would: given only the score and the events that happened up to some minute T (goals, cards, subs — nothing from after T), can the model correctly identify who currently has the upper hand, what the live threats are, and make specific, checkable predictions about how the rest of the match will unfold (next goal, final result, next clear chance)?

Two properties make this a meaningful test of situational reasoning rather than memorized knowledge:

1. **It is genuinely partial.** The model never sees the outcome. It has to project forward from an incomplete, still-changing state, the same way a live analyst does — not summarize a match it already knows the ending to.
2. **It must update correctly over time.** If the same match is frozen at minute 20, 45, and 70, the model's read should shift in the right direction as new information (a red card, a goal, a substitution) arrives. A model that gives the same generic answer regardless of freeze point isn't reasoning about the state — it's pattern-matching on team names or priors.

This is different from, and harder than, pre-match prediction (which conditions on fixed priors before anything has happened) and different from post-hoc match summarization (which conditions on the full, known outcome). Pulse sits in between: it measures whether a model's live situational judgment is any good, and whether that judgment tracks new evidence sensibly as the game evolves.
