# Troubleshooting

## GNOME's “Stop Sharing” button destroyed the virtual monitors

The monitor-with-arrow status indicator includes the daemon's `RecordVirtual` sessions. Clicking **Stop Sharing** closes those sessions, removes the `Meta-*` outputs, and can invalidate Sunshine's saved Portal selections.

Recover in this order:

```bash
systemctl --user stop app-dev.lizardbyte.app.Sunshine.Android.service
systemctl --user stop app-dev.lizardbyte.app.Sunshine.service
systemctl --user restart gnome-virtual-monitor.service
journalctl --user -u gnome-virtual-monitor.service -n 30 --no-pager
systemctl --user start app-dev.lizardbyte.app.Sunshine.service
systemctl --user start app-dev.lizardbyte.app.Sunshine.Android.service
```

Wait for `Display layout applied` before starting Sunshine. If an instance still reports a Portal error, reset only that instance's token as described below.

## Portal returns no streams or Moonlight says “No video received”

A restore token can refer to an output that no longer exists. Stop the affected instance, move (do not publish) its token to a private backup, then restart and select exactly one output.

For Android:

```bash
unit=app-dev.lizardbyte.app.Sunshine.Android.service
token="$HOME/.config/sunshine-instances/android/sunshine/portal_token"
backup="$HOME/.local/state/gnome-virtual-monitor-token-backups/$(date +%Y%m%d-%H%M%S)"
systemctl --user stop "$unit"
install -d -m 700 "$backup"
if [[ -f "$token" ]]; then mv "$token" "$backup/android.portal_token"; fi
systemctl --user start "$unit"
```

For the common native/default instance, use unit `app-dev.lizardbyte.app.Sunshine.service` and token `~/.config/sunshine/portal_token`. Package layouts vary, so confirm the path before moving anything.

The Portal selector must remain open until you choose the correct monitor and click **Share**. The 2340x1080 phone output is the wide one; the laptop is 1366x768.

## Wrong output reaches a client

Check the Sunshine log for the logical offset and the negotiated physical `Size`. Do not hard-code `Meta-0`: connector numbering changes whenever sessions are recreated. Reset only the wrong instance's Portal token and reselect its intended output.

## Moonlight shows `Desktop`, `Desktop`, and `Steam`

The client probably reached the normal Sunshine instance instead of the isolated Android instance, or Android's `apps.json` was not copied into its nested config directory.

Confirm that Moonlight added `HOST_IP:48049` and that this file exists:

```text
~/.config/sunshine-instances/android/sunshine/apps.json
```

The supplied Android app name is `Android Monitor`.

## Cursor freezes, duplicates, or leaves a ghost at 175% scale

This is a known Mutter 46 fractional-screencast cursor bug, not an H.264 or NVENC failure. Sunshine's Portal backend requests an embedded cursor, so Mutter paints it directly into the captured frame. See [Mutter issue #3613](https://gitlab.gnome.org/GNOME/mutter/-/issues/3613), [Ubuntu bug #2078460](https://bugs.launchpad.net/ubuntu/+source/mutter/+bug/2078460), and [Sunshine's embedded Portal cursor mode](https://github.com/LizardByte/Sunshine/blob/v2026.516.143833/src/platform/linux/portalgrab.cpp#L395-L408).

First ensure Moonlight is using the native 2340x1080 stream rather than 1280x720. Then reload the cursor texture without changing layout:

```bash
old_size=$(gsettings get org.gnome.desktop.interface cursor-size)
gsettings set org.gnome.desktop.interface cursor-size 32
gsettings set org.gnome.desktop.interface cursor-size "$old_size"
```

Changing to another installed cursor theme and back can produce the same reload. These settings affect the entire GNOME session.

If the bug persists, the robust fallback is to avoid fractional capture scaling: configure the phone virtual output as 1326x612 with `scale = 1.0`, let Moonlight upscale it to 2340x1080, restart the daemon, and renew the Android Portal token. The 1326x612 mode keeps the phone's 13:6 landscape ratio and roughly preserves the apparent 175% UI size, but text is less sharp.

## The phone still runs at 60 FPS

Three independent controls must all allow 120:

1. the phone monitor in `config.toml` uses `refresh = 120`;
2. the Galaxy A56 uses **Display > Motion smoothness > Adaptive**, with power saving disabled; and
3. Moonlight requests 120 FPS.

Reconnect after changing Moonlight. In the Sunshine log, ignore 60 FPS encoder-probe lines emitted before connection; find `Requested frame rate [120fps]` after `New streaming session started`. Use Moonlight's overlay to verify incoming and rendered FPS under motion.

## Fractional scale is unavailable

Confirm `scale-monitor-framebuffer` is present in `org.gnome.mutter experimental-features` and `GetCurrentState` reports logical layout mode. The daemon rejects a requested scale when Mutter's nearest supported value differs by more than 0.05.

## Sunshine starts before the outputs exist

Current example units wait for `$XDG_RUNTIME_DIR/gnome-virtual-monitor.ready`. If Sunshine's `ExecStartPre` times out, inspect the daemon first:

```bash
systemctl --user status gnome-virtual-monitor.service
journalctl --user -u gnome-virtual-monitor.service -n 50 --no-pager
```

Fix its configuration or dependencies rather than replacing the readiness check with a fixed sleep.

## Android touch lands on another monitor

Use Moonlight's touchscreen-as-trackpad behavior. Absolute touch coordinates for a selected non-primary output remain unreliable in Sunshine on Linux.

## Sunshine reports encoder errors during startup

Encoder discovery intentionally tries multiple paths and can emit safe failures. For the validated NVIDIA path, the final discovery/session lines must show `Found H.264 encoder: h264_nvenc` and `Creating encoder [h264_nvenc]`.
