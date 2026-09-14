# `bmad/` — the doctrine layer

This folder is the adaptation of a BMAD-style agent structure to this project. It holds the parts
of the harness that are **surface-independent**: workflows, checklists, and the policy fragments
that every agent must obey regardless of whether it is running in GitHub Copilot, Continue, or a
terminal.

## Why this layer exists

There are three agent surfaces in this repository and there will probably be more:

```text
                        AGENTS.md                 ← the map, read by everything
                            │
                        bmad/                     ← doctrine: workflows, checklists, policy
                       ╱    │    ╲
        .github/           .continue/          (a human with a terminal)
   copilot-instructions   config.yaml
   agents/*.agent.md      rules/*.md
   prompts/*.prompt.md    prompts in config
   instructions/*.md
```

Without this layer, the same rule ("never index a corpus before a human has read the
anonymisation report") gets written three times, drifts, and then means three different things.
With it, each surface is a thin adapter: the frontmatter is surface-specific, the body links here.

**The rule: doctrine changes are made in `bmad/` or `AGENTS.md` first, and the adapters are
updated to point at them. Never the other way round.**

## What is where

| Path | Contents |
|---|---|
| `bmad/agents/` | Role charters — what each agent is for, what it may touch, when it must stop. Surface-neutral prose. |
| `bmad/workflows/` | Multi-step procedures that chain agents. Each has an entry condition, steps, and an exit condition. |
| `bmad/checklists/` | Things a human ticks. The definition of done, and session readiness. |

## Adaptation notes

Adapted from a BMAD-style layout with five role agents, with three deliberate changes:

1. **Roles were re-cut for this project.** The generic analyst/architect/author/qa/packager set
   became `@curator` / `@librarian` / `@author` / `@qa` / `@packager`, because two of this
   project's real jobs — corpus hygiene and assistant evaluation — have no equivalent in a
   software-only agent set, and an architect role has nothing to do in a repository whose
   architecture is four folders and a Makefile.
2. **`@qa` is read-only.** In the original layout QA can edit. Here it cannot, because the whole
   package teaches generator/evaluator separation and a QA agent that fixes what it finds is the
   exact failure the teaching material warns about.
3. **The definition of done is a command, not a document.** `make verify` exits 0 or it does not.
   The checklists supplement it; they do not replace it.

## Chaining

Workflows are implemented on the Copilot side as **handoffs** in the agent frontmatter, so a
facilitator moves `@curator → @librarian → @qa → @packager` by pressing a button rather than by
remembering the order. Continue has no handoff mechanism, so there the same chain is documented in
`bmad/workflows/` and each step is a slash command.
