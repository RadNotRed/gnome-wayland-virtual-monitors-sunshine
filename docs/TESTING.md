# Testing

## Automated

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m gnome_virtual_monitors \
  --config config/three-monitors.example.toml --check-config
python3 -m compileall -q src
bash -n scripts/*.sh
python3 -m json.tool experimental/sunshine/apps.json.example >/dev/null
systemd-analyze --user verify \
  systemd/gnome-virtual-monitor.service \
  experimental/systemd/app-dev.lizardbyte.app.Sunshine.Android.service
git diff --check
```

## Host acceptance

- Every active physical monitor retains its current mode, refresh, transform, scale and primary status (legacy mode uses configured refresh).
- Laptop virtual output appears on the physical left.
- Phone virtual output appears centered below the primary.
- Phone scale is the closest supported value to the requested scale.
- Both virtual outputs have distinct PipeWire node IDs.
- The daemon publishes its readiness marker only after the layout is applied.
- Both Sunshine instances report DMA-BUF and H.264 NVENC.
- Restarting only Sunshine preserves each correct Portal selection.
- Recreating virtual outputs through a daemon restart is tested separately because it may stale a Portal token.
- Restarting the daemon leaves no ghost `Meta-*` outputs.

## Client acceptance

- Both clients connect at the same time and receive different content.
- Android reports hardware H.264 decoding through MediaCodec/Exynos.
- Android reports 2340x1080 incoming/rendered video near 120 FPS while content is moving.
- Windows remains 1366x768 at 60 FPS while the primary stays at 120 Hz.
- Thirty-minute run has no material packet loss, runaway memory use or physical-refresh regression.
- Reconnect, Sunshine restart, login restart and suspend/resume are tested separately.
- Android 120 FPS is accepted only if it improves latency without decode drops, jitter or thermal instability.
- Cursor movement is tested across the entire 175%-scaled phone output; any ghosting is recorded as the known Mutter issue.

## Multi-physical acceptance matrix

Test 1 physical + 1 virtual, 2 physical + 1 virtual, and 3 physical + 1 virtual.
Include landscape + portrait, mixed refresh, mixed scale, and mirrored physical
groups. Compare `GetCurrentState` before and after: every original connector and
current mode ID must remain present, with the same transform, scale and primary.
Positions must match except a common origin translation for left/above placement.
Test two virtual roles and chained relative placement as well as the original
example. A same-resolution physical display or pre-existing virtual output must
not become a newly created role. Test ambiguous new virtual outputs and unplugged
physical connectors: verification must fail without publishing readiness.

Back up configuration and installed source before replacing a working setup.
Stop Sunshine instances before testing daemon stop/restart. Confirm that stopping
the daemon removes its virtual outputs and leaves a usable physical desktop.
Never use GNOME's global Stop Sharing control for this test.
