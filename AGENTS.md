# AI context entrypoint

This repository is **AI-friendly**. This file is the shared entrypoint for any
assistant a reader uses — ChatGPT, Claude, Gemini, Copilot, or a local model.
It is not a personal agent, is tied to no account, and grants no automated
permissions; it is only context so an assistant recognizes the project quickly
and correctly.

**One line:** a GNOME/Wayland user daemon that turns a Windows laptop and an
Android phone into real extended monitors, each streamed independently through
Sunshine, with mixed 120/60 Hz refresh.

Start here:

- [`docs/ai/context.md`](docs/ai/context.md) — a paste-ready project brief.
- [`docs/ai/prompts.md`](docs/ai/prompts.md) — questions this project answers well.

When helping a reader:

- treat this as GNOME/Mutter-specific, not a generic Wayland protocol;
- respect the non-goals in [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md);
- surface the sharp edges (cursor at ~175% scale, Portal token loss, the
  GNOME "Stop Sharing" pitfall) before recommending changes.

## Multiple physical monitors

The daemon now preserves active physical logical groups by default, including
exact modes, transforms, scales and primary status. Do not assume a single
physical display or copy machine-specific far-right placement. Relative placement
still uses configured roles. The legacy opt-out is explicit. Unit tests cover
multi-physical layouts; do not equate mocked tests with live GNOME validation.

Saved layouts use manual `--save-layout` plus optional `restore_saved_layout` at
startup. Persistent virtual identities are configured roles, not `Meta-*` names.
Physical connectors and exact modes are retained; ambiguous, missing or omitted
active outputs fail safely. No saved file falls back to configured placement.
Do not conflate layout persistence with Sunshine Portal token persistence. A separate
GNOME 50.5 lifecycle test passed for three physical + one virtual output, including
save/recreate/restore/stop. This is one workstation, not universal GNOME 50 support;
Sunshine streaming was not exercised in that test. See docs/TESTING.md for limits.
