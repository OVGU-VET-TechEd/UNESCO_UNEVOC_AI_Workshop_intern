# Checklist — definition of done

For any item moving from `in_progress` to `passing` in `feature_list.json`.

- [ ] `make verify` exits **0**, and its full output is pasted into the item's `evidence` field.
- [ ] Exactly one item was `in_progress` while the work happened.
- [ ] If code changed: `make demo` was run and completed.
- [ ] If the demo assistant changed: `make eval` was run and **all three rates** are recorded —
      retrieval hit, answered-when-expected, refused-when-expected.
- [ ] If the corpus changed: a human read `anonymisation_report.md` and said so, by name, in
      `PROGRESS.md`.
- [ ] If prose changed: every new external claim names its source in the text.
- [ ] If a threshold changed: the `eval_kb.py` run justifying it is quoted, before and after.
- [ ] `PROGRESS.md` has a session record appended — goal, completed, verification, evidence path,
      risks, next best action.
- [ ] Nothing generated was committed: no `harness_state.json`, `ask_log.md`, `output_*/`,
      `__pycache__/`.

**If any box is unticked, the item is not `passing`. It is `in_progress` or `blocked`.** There is
no third state and no "done except for".
