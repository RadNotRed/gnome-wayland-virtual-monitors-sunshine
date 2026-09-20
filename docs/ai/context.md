# Project context for AI assistants

Paste this file into ChatGPT, Claude, Gemini, Copilot, or a local model
before asking about the repository. It is shared context for whatever
assistant a reader happens to use — it is not tied to any account and grants
no automated permissions.

## One paragraph

This project is a GNOME/Wayland user-session daemon that adds **real extended
monitors** to an existing physical desktop. It asks Mutter for `RecordVirtual`
outputs, keeps their PipeWire nodes alive, and preserves active physical logical
groups while adding configured virtual roles. Optional saved layouts retain manual
position, scale, orientation and primary changes across recreation. Virtual roles
are identified by configuration, not temporary connector names. Each output can
be captured by an isolated Sunshine instance through the XDG Desktop Portal and
viewed in Moonlight on a laptop, TV, tablet or phone. The original laptop/phone
configuration remains a working example with independent mixed refresh rates.

## What it is not

- Not a compositor-independent Wayland protocol — it is GNOME/Mutter specific.
- Not mirroring — windows genuinely move beyond the edge of the primary display.
- Not a kernel module or a root daemon — the installer stays inside `$HOME`.
- Not affiliated with GNOME, Sunshine, LizardByte, Moonlight, NVIDIA,
  Microsoft, or Samsung.

## Architecture, briefly

- `src/gnome_virtual_monitors/` — the Python daemon: config, layout model,
  Mutter D-Bus calls, PipeWire node keep-alive, and a readiness loop.
- Mutter's private `RecordVirtual` interface creates the virtual outputs.
- PipeWire + GStreamer `pipewiresrc` carry each output's frames.
- Sunshine captures each output via XDG Portal; two isolated Sunshine
  identities run at once (laptop + phone) so their state never collides.
- Moonlight (desktop and Android) decodes with hardware H.264.

## Validated stack

Zorin OS 18 (Ubuntu 24.04) · GNOME Shell & Mutter 46.2 on Wayland · NVIDIA
GTX 1650 driver 595.71.05 · Sunshine 2026.516.143833 · PipeWire 1.0.5 ·
GStreamer `pipewiresrc`. Displays: physical primary 1920×1080@120, Windows
laptop 1366×768@60 (left), Galaxy A56 2340×1080@120 ~175% scale (below).

## Sharp edges to surface before suggesting changes

- Mutter 46 can corrupt the embedded cursor around 175% screencast scaling;
  the documented fallback keeps UI size at the cost of some sharpness.
- Do not click **Stop Sharing** in GNOME's monitor-with-arrow indicator while
  virtual displays are active — it destroys the outputs and can stale
  Sunshine's Portal tokens.
- Recreating virtual outputs can invalidate saved Portal selections.
- Two Sunshine processes isolate capture and state, not input ownership.
- Suspend/resume and newer GNOME versions still need wider testing.

## How to help a reader

Respect the promises and non-goals in [`../PROJECT_SCOPE.md`](../PROJECT_SCOPE.md),
lean on [`../ARCHITECTURE.md`](../ARCHITECTURE.md) for internals, and send
pairing/latency questions to [`../SUNSHINE.md`](../SUNSHINE.md). When unsure
whether behavior is a bug or a known limitation, check
[`../TROUBLESHOOTING.md`](../TROUBLESHOOTING.md) first.

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
