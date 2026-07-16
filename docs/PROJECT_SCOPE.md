# Project scope and acceptance

## Goal

Provide a reproducible, user-session-only way to create extended virtual monitors on GNOME Wayland and stream a different monitor to each Moonlight client through Sunshine with low interactive latency.

## Validated layout

- Keep the physical 1920x1080 primary display at 120 Hz.
- Place a 1366x768, 60 Hz Windows-laptop output to the physical left.
- Place a landscape 2340x1080, 120 Hz Galaxy A56 output centered below the primary.
- Request approximately 175% GNOME scale for the phone so text and controls remain readable.
- Preserve mixed refresh rates rather than reducing the entire desktop to 60 Hz.

## Streaming requirements

- Capture each virtual output through a separate Sunshine/XDG Portal identity.
- Keep tokens, ports, credentials, certificates, and pairing state isolated.
- Use H.264 hardware encoding through NVENC on the validated NVIDIA host.
- Use hardware H.264 decoding on Windows and Android when available.
- Support direct LAN/Wi-Fi and routed private networks such as Tailscale.
- Run the phone at 120 FPS only when the virtual mode, Android panel, and Moonlight all request 120.
- Keep the phone UI legible and use trackpad-style touch input on the non-primary output.

## Operational requirements

- Install without a root daemon or kernel module.
- Start in the graphical user session and wait for the monitor layout before Sunshine capture.
- Reject ambiguous monitor roles, an unavailable physical mode, cyclic placement, and invalid numeric configuration before creating outputs.
- Preserve unrelated Mutter experimental features during uninstall.
- Document Portal reauthorization, GNOME's Stop Sharing failure mode, the Mutter fractional-scale cursor bug, rollback, testing, and sensitive files.
- Credit Lina as creator and maintainer.

## Acceptance signals

- The daemon reports `1920x1080@120`, `1366x768@60`, and `2340x1080@120` in one applied logical layout.
- The laptop and phone connect concurrently and receive different extended-desktop regions.
- The Android Sunshine session reports the phone stream, physical `Size: 2340x1080`, `Requested frame rate [120fps]`, and `Creating encoder [h264_nvenc]`.
- Moonlight's overlay reports hardware decoding and approximately 120 incoming/rendered FPS while content is moving.
- Restarting a Sunshine process preserves a valid selection; recreating outputs has a documented token-renewal path.

## Non-goals

- A compositor-independent Wayland protocol.
- Guaranteed zero latency or guaranteed 120 FPS on every network/client.
- Separate keyboard and pointer seats per client.
- Preserving additional physical monitors in v0.1; the validated scope manages one physical primary plus virtual outputs.
- Treating a plain USB-C cable as a network link without tethering or a network adapter.
