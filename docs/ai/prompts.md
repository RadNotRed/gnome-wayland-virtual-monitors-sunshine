# Ready-to-use prompts

Copy a prompt, paste [`context.md`](context.md) above it, and send both to any
assistant. These are the questions this project answers well.

## Understand the setup

> Read the project context above. In three sentences, explain what this daemon
> does and why it needs Mutter's `RecordVirtual` interface instead of a normal
> multi-monitor setup.

## Adapt it to my hardware

> Here is the validated stack in the context. My machine is `<GPU / GNOME
> version / displays>`. Which values in `config/three-monitors.example.toml`
> do I change, and which sharp edges apply to my setup?

## Diagnose a problem

> Using the context and TROUBLESHOOTING.md, my symptom is `<describe>`. Is this
> a known limitation or a misconfiguration? Give me the smallest first check.

## Review a change safely

> I want to `<change>`. Given the non-goals in PROJECT_SCOPE.md and the sharp
> edges, tell me what could break — Portal tokens, cursor scaling, or the
> "Stop Sharing" pitfall — before I touch anything.

## Multiple physical monitors

The daemon now preserves active physical logical groups by default, including
exact modes, transforms, scales and primary status. Do not assume a single
physical display or copy machine-specific far-right placement. Relative placement
still uses configured roles. The legacy opt-out is explicit. Unit tests cover
multi-physical layouts; do not equate mocked tests with live GNOME validation.

## Preserve a customized desktop

> My host has `<count>` physical monitors with `<rotations/scales>` and configured
> virtual roles `<names/resolutions>`. Explain how to save the active layout and
> enable restoration without depending on temporary Meta connectors. Before a
> live test, back up config and installed source and stop capture instances first.
> Distinguish mocked tests, verify-only checks and actual output lifecycle testing.
