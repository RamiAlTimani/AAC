# Reflection

## Tools used

One AI tool was used for this project: the **Claude Code VS Code extension**, running inside the editor with direct access to the project files. It was used for three things: writing tests for the two new features (due dates and tags), building the frontend for those features, and drafting documentation such as the mini-ADR and user stories.

## Where AI helped

Tests and frontend code were much faster. Once the backend rules for due dates and tags were settled, a request for tests produced a working set in minutes, including edge cases that would otherwise have been missed. The frontend followed the same pattern: form fields, tag input, and due-date display came together far faster than writing them by hand.

## Where AI slowed things down

The mini-ADR went badly. Without the full context of the project, the tool kept proposing architectures as if the work were starting from zero: new frameworks, new folder layouts, new data models. The actual decision was much narrower, namely how to extend an existing task tracker with two features.

## Where review changed the result

The AI assumed that tasks could be given a due date in the past. That was never a requirement: backdated due dates should not be allowed at all. The assumption was never stated anywhere, so it was only caught by reviewing the work rather than accepting it as correct. The rule was then corrected to reject past dates.
