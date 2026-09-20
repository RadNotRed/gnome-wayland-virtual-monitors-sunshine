# Rollback

Stop both capture processes before destroying their selected outputs:

```bash
systemctl --user disable --now app-dev.lizardbyte.app.Sunshine.Android.service
systemctl --user stop app-dev.lizardbyte.app.Sunshine.service
```

Stop and disable the virtual monitor daemon:

```bash
systemctl --user disable --now gnome-virtual-monitor.service
```

Remove the installed daemon. If the installer added `scale-monitor-framebuffer`, the uninstaller removes only that feature and preserves unrelated Mutter features added later:

```bash
./scripts/uninstall-user.sh
```

The uninstaller removes the normal-Sunshine readiness drop-in but intentionally preserves monitor configuration, Sunshine pairing state, Portal tokens, credentials and certificates. The Android unit and its isolated config directory also remain installed but disabled. Delete those only after reviewing the paths manually.

If the display layout is unusable, stopping `gnome-virtual-monitor.service` destroys the virtual outputs and leaves the physical monitors available. Log out and back in after restoring the original Mutter setting if GNOME does not immediately return to physical layout mode.

If you backed up configuration before testing, restore that directory after
stopping the daemon. Confirm the normal physical arrangement in GNOME Settings
and compare modes, refresh, transforms, primary and relative positions. Mutter
may return to its stored physical-only origin after the virtual outputs disappear.

## Saved layout and configuration rollback

The uninstaller intentionally preserves `layout.json` alongside user configuration.
To disable restoration, set `restore_saved_layout = false` before restarting.
To reset the save after stopping capture and the daemon:

```bash
state="${XDG_STATE_HOME:-$HOME/.local/state}/gnome-wayland-virtual-monitors-sunshine/layout.json"
if [ -f "$state" ]; then mv -- "$state" "$state.backup-$(date +%Y%m%d-%H%M%S)"; fi
```

Restore your pre-test `~/.config/gnome-virtual-monitors` backup if necessary. If you
replaced installed Python sources, restore that backup too before restarting an
older version. The repository examples never overwrite an existing config during
installation. Confirm all normal physical displays, their orientations, refresh,
scale and primary in GNOME Settings before restarting any capture process.
