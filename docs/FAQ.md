# FAQ

## I rebooted (or the daemon restarted) and now Moonlight can't connect / shows no video

This is the most common surprise, so it gets its own answer.

Every time the virtual-monitor daemon restarts, it recreates the virtual
outputs from scratch and their PipeWire node IDs change. Sunshine saved a
Portal "restore token" that points at the old nodes, so on the next start it
asks the Portal to restore a stream that no longer exists. You'll see this in
the instance's log:

```
[portalgrab] RemoteDesktop Start: no streams in response
[portalgrab] Failed to connect to portal
[pipewire] Could not find display with name: ''
Fatal: Unable to find display or encoder during startup.
```

The instance may still listen on its pairing port, so it looks "active", but
any connection fails. Each Sunshine instance has its own token, so the laptop
and the phone can break independently.

**Fix — reset the stale token and reauthorize:**

```bash
# native/default instance (the Windows laptop)
systemctl --user stop app-dev.lizardbyte.app.Sunshine.service
mv ~/.config/sunshine/portal_token ~/.config/sunshine/portal_token.bak
systemctl --user start app-dev.lizardbyte.app.Sunshine.service

# isolated Android instance (the phone)
systemctl --user stop app-dev.lizardbyte.app.Sunshine.Android.service
mv ~/.config/sunshine-instances/android/sunshine/portal_token \
   ~/.config/sunshine-instances/android/sunshine/portal_token.bak
systemctl --user start app-dev.lizardbyte.app.Sunshine.Android.service
```

Only reset the instance that actually failed. When the **Remote desktop**
dialog appears, keep "Remember this selection" checked and pick the right
screen (see the next question), then click **Share**. The instance finishes
starting and begins listening on its real ports.

Full detail: [Troubleshooting → Portal returns no streams](TROUBLESHOOTING.md#portal-returns-no-streams-or-moonlight-says-no-video-received).

## Which screen do I pick in the "Remote desktop" dialog?

The dialog draws the screens in their physical layout. Match by position:

- **Left of your physical monitor** → the Windows laptop output (1366x768).
- **Below your physical monitor** → the phone output (2340x1080, the wide one).
- **Your physical monitor itself** → never pick this. Selecting it streams your
  real screen instead of the virtual one.

Do not rely on the connector name (`Meta-0`, `Meta-1`): the numbering changes
whenever the outputs are recreated. Go by position and resolution.

## No virtual monitors appear at all and the daemon keeps restarting

The daemon crash-loops on an invalid config. Check its log:

```bash
journalctl --user -u gnome-virtual-monitor.service -n 20
```

A missing or malformed field fails validation, for example:

```
Invalid configuration: primary.width must be a positive integer
```

The `[primary]` section needs `width` and `height` (plus `connector` and
`refresh`) that match your physical display. Fix the config, then clear the
crash counter and start it again:

```bash
systemctl --user reset-failed gnome-virtual-monitor.service
systemctl --user restart gnome-virtual-monitor.service
```

A healthy start logs `Display layout applied`. If only your physical connector
shows up in `GetCurrentState` and no `Meta-*` outputs, the daemon never
finished — check the config first.

## Do I have to reauthorize the Portal every time?

No. With "Remember this selection" checked, the token survives normal use. You
only reauthorize when the outputs get recreated — a reboot, a daemon restart,
or after clicking GNOME's "Stop Sharing" indicator. If reauthorizing every
session, confirm the checkbox stays ticked and that nothing is restarting the
daemon in the background.

## Can I use this project however I want?

Yes. It's released into the public domain under [The Unlicense](../LICENSE) —
copy it, modify it, ship it, sell it, no attribution required.
