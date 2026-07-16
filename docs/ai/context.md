# Project context for AI assistants

Paste this file into ChatGPT, Claude, Gemini, Copilot, or a local model
before asking about the repository. It is shared context for whatever
assistant a reader happens to use — it is not tied to any account and grants
no automated permissions.

## One paragraph

This project is a GNOME/Wayland user-space daemon that turns a Windows laptop
and an Android phone into **real extended monitors** for a single Ubuntu
desktop. It asks Mutter for `RecordVirtual` virtual outputs, keeps their
PipeWire nodes alive, and applies an extended layout. Each virtual output is
captured by its own isolated Sunshine instance through the XDG Desktop Portal
and viewed in Moonlight on the client. The result is one desktop spread
across three surfaces with independent, mixed refresh rates (120 Hz where it
matters, 60 Hz on the laptop).

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
