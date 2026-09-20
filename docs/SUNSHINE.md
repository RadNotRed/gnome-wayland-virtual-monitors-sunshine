# Sunshine and Moonlight setup

The commands below retain the original Windows-laptop and Android examples. The same isolated client-instance model applies to TVs, laptops, tablets and phones. The two processes must never share Portal tokens, ports, credentials, certificates, or pairing state.

The supplied units assume a native Sunshine package at `/usr/bin/sunshine` and an NVIDIA GPU. Adapt `ExecStart` for another installation format and choose the appropriate encoder for Intel/AMD. Flatpak and AppImage layouts are not drop-in replacements for these examples.

## 1. Confirm the virtual outputs

```bash
systemctl --user enable --now gnome-virtual-monitor.service
journalctl --user -u gnome-virtual-monitor.service -n 30 --no-pager
```

The example layout should contain:

```text
primary  1920x1080 @ 120 Hz
laptop   1366x768  @  60 Hz
phone    2340x1080 @ 120 Hz, scale approximately 1.75
```

Mutter will probably call the virtual connectors `Meta-0` and `Meta-1`, but those numbers are not stable. Identify an output by its mode, logical position, and Portal thumbnail.

## 2. Configure the normal instance for the laptop

The normal Sunshine instance uses base port `47989`, Web UI port `47990`, and its usual config root (commonly `~/.config/sunshine`). In Sunshine's Web UI, select Portal capture and the hardware encoder for your GPU.

The main installer adds a systemd drop-in that makes the normal instance wait for the virtual layout. Confirm it is present:

```bash
systemctl --user cat app-dev.lizardbyte.app.Sunshine.service
```

If your Sunshine unit has a different name, move the drop-in to that unit's `.service.d/` directory before starting capture. Restart the normal instance after the daemon reports readiness. In GNOME's Portal dialog, select only the 1366x768 laptop output. Pair Moonlight on Windows with this normal instance and use:

- 1366x768 at 60 FPS;
- H.264 with hardware decoding enabled when supported;
- approximately 12-18 Mbps to start; and
- the performance overlay during validation.

The normal instance's Portal token is separate from Android's. With the common native layout it is `~/.config/sunshine/portal_token`.

## 3. Install the isolated Android instance

From the repository root:

```bash
install -d -m 700 "$HOME/.config/sunshine-instances/android/sunshine"
install -m 600 experimental/sunshine/android.conf.example \
  "$HOME/.config/sunshine-instances/android/sunshine/sunshine.conf"
install -m 600 experimental/sunshine/apps.json.example \
  "$HOME/.config/sunshine-instances/android/sunshine/apps.json"
install -d -m 755 "$HOME/.config/systemd/user"
install -m 644 \
  experimental/systemd/app-dev.lizardbyte.app.Sunshine.Android.service \
  "$HOME/.config/systemd/user/app-dev.lizardbyte.app.Sunshine.Android.service"
systemctl --user daemon-reload
systemctl --user start app-dev.lizardbyte.app.Sunshine.Android.service
```

The unit name gives the process a distinct Portal app identity. Its `XDG_CONFIG_HOME` is `~/.config/sunshine-instances/android`, so Sunshine stores files under the nested `sunshine/` directory. The unit waits for the daemon's readiness marker instead of sleeping for a fixed duration.

Do not enable automatic startup until capture and pairing work.

## 4. Authorize the phone output

The first Android-instance start opens GNOME's screen-selection dialog while Sunshine tests encoders. Select exactly one output: the wide 2340x1080 phone monitor. Do not select the physical monitor or the 1366x768 laptop output.

The Android choice is saved in:

```text
~/.config/sunshine-instances/android/sunshine/portal_token
```

Treat the token as sensitive local state. Never commit, share, edit, or copy it between instances. If the selector does not open or Sunshine reports `no streams in response`, use the reset procedure in [Troubleshooting](TROUBLESHOOTING.md).

## 5. Create credentials and pair Android

On the **Ubuntu host**, open:

```text
https://localhost:48050
```

The locally generated HTTPS certificate may trigger a browser warning on first use. Confirm that the address is exactly `localhost:48050`, continue locally, and create credentials.

Find the host's LAN address with `ip address` or your router. Prefer the direct address on the same Ethernet/Wi-Fi network for the lowest latency. A Tailscale address also works when direct routing is unavailable, but may take a longer path.

In Moonlight Android, manually add:

```text
HOST_IP:48049
```

Moonlight displays a four-digit PIN. Enter it on the **PIN** page in the host's Sunshine Web UI. The app list for this instance should contain `Android Monitor`; seeing only `Desktop`, `Desktop`, and `Steam` usually means Moonlight reached the normal instance instead.

After a successful test:

```bash
systemctl --user enable app-dev.lizardbyte.app.Sunshine.Android.service
```

## 6. Configure the Galaxy A56 for 120 FPS

On the phone:

```text
Settings > Display > Motion smoothness > Adaptive
```

Disable power saving while testing because Samsung may limit the panel to 60 Hz. In Moonlight Android, start with:

- resolution: native 2340x1080 in landscape;
- frame rate: 120 FPS;
- bitrate: 28 Mbps, raising toward 35 Mbps only if the network stays stable;
- video codec: prefer H.264;
- frame pacing: the lowest-latency option;
- stretch video: disabled;
- performance overlay: enabled; and
- input: touchscreen-as-trackpad for a non-primary Linux output.

NVENC is NVIDIA's hardware video encoder on the Ubuntu host. MediaCodec is Android's hardware decoding interface on the phone. The overlay should show hardware H.264 decoding with low decode time; otherwise the phone may be decoding in software.

The example disables HEVC and AV1 advertisement to force the validated H.264/NVENC path. Moonlight controls resolution and requested FPS; Sunshine 2026.516 ignores `resolutions` and `fps` in `sunshine.conf`. Audio is intentionally disabled for the Android instance so two Sunshine processes do not compete for the same desktop audio path.

## 7. Verify the negotiated session

Connect from the phone, move a window on the virtual output, then inspect the host:

```bash
journalctl --user \
  -u app-dev.lizardbyte.app.Sunshine.Android.service \
  --since "-5 minutes" --no-pager \
  | grep -E 'New streaming session|Found stream|Requested frame rate|Size:|Creating encoder|Streaming bitrate'
```

At approximately 175% scale, a successful session reports values equivalent to:

```text
New streaming session started
Found stream for display ... resolution: 1339x618
Requested frame rate [120fps]
Size: 2340x1080
Creating encoder [h264_nvenc]
Streaming bitrate is 28000000
```

`1339x618` is the GNOME logical size used to place windows; `2340x1080` is the physical PipeWire capture. Encoder probes during Sunshine startup may request 60 FPS. The relevant 120 FPS line appears **after** Moonlight starts its streaming session.

Negotiation is not proof of smooth delivery. While content is moving, use Moonlight's overlay to check incoming/rendered FPS, packet loss, decode time, jitter, and dropped frames. A static desktop may produce fewer unique frames even when the session target is 120 FPS.

## Network, firewall, and input security

- Prefer Ethernet or clean 5 GHz/6 GHz Wi-Fi. A plain USB-C cable is not a network transport unless USB tethering or a network adapter creates an IP link.
- The Android base port `48049` uses TCP `48044`, `48049`, `48050`, and `48070`, plus UDP `48058-48060`. If a firewall blocks them, allow them only from the trusted client subnet/interface.
- The example disables UPnP and restricts its Web UI to the host PC.
- `lan_encryption_mode = 0` minimizes overhead but disables Sunshine's optional LAN stream encryption. Use it only on a trusted LAN or inside an already encrypted tunnel; choose mode `1` or `2` otherwise.
- Never expose either Sunshine port family or Web UI directly to the public Internet.
- A paired Moonlight client can control keyboard and pointer input in the GNOME session. Pair only trusted devices.
- Two Sunshine instances share the same GNOME input seat. The setup isolates capture and state, not input ownership.

## Other client instances and custom ports

To create an instance for a TV or another client, copy the Android example under
a new service name (for example `app-dev.lizardbyte.app.Sunshine.Client.service`)
and change `XDG_CONFIG_HOME` to a unique root such as
`%h/.config/sunshine-instances/client`. Place `sunshine.conf` and `apps.json` in its
nested `sunshine/` directory, with private directory/file permissions (0700/0600).
Change the app's display name to suit the client. Keep the readiness `ExecStartPre`,
`BindsTo` and `After` dependencies in each service. Do not combine identities into
one process, copy tokens/credentials/certificates between instances, or overwrite
an already paired config. Create new credentials and pair each instance separately.

For base port **P**, the documented port family is TCP **P−5, P, P+1, P+21** and UDP
**P+9 through P+11**. The Web UI uses **P+1**; Moonlight's manual host entry uses
**HOST_IP:P**. For the retained example P=48049, the Web UI is 48050. Select a base
whose entire family does not overlap any other instance and permit only the needed
trusted-network traffic. Keep unique XDG roots, pairing state, certificates,
credentials, Portal tokens and ports even when both clients have the same type.

After daemon readiness, select exactly the desired virtual monitor in the Portal
dialog using its thumbnail, mode and position. `Meta-*` numbering is temporary.
A saved daemon layout restores geometry, not Portal authorization; recreating an
output may still require reauthorizing the affected Sunshine instance only.
