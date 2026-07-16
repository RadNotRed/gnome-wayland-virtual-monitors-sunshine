# Security

## Report a vulnerability

Do not open a public issue containing credentials, certificates, Portal tokens, pairing data, IP addresses, or full Sunshine logs. Use GitHub's private vulnerability-reporting form for this repository.

## Sensitive files

Never commit:

- `sunshine_state.json`
- `portal_token`
- Sunshine `credentials/` or any PEM/key file
- real `sunshine.conf` files containing local paths or network details
- real `apps.json` files containing local commands or paths
- diagnostic bundles without manual review
- pairing PINs, Tailscale identities, EDID serials, hostnames, or user names

Each Sunshine instance should use its own `XDG_CONFIG_HOME`, app ID, state, certificates, and Portal token. The experimental Android service uses `UMask=0077`.

Keep Sunshine Web UI access restricted to the local PC unless you understand the authentication and CSRF implications. Disable UPnP unless it is explicitly required.

The low-overhead example uses `lan_encryption_mode = 0`, which disables Sunshine's optional LAN stream encryption. Use it only on a trusted local network or inside an already encrypted tunnel. Prefer mode `1` or `2` when other devices on the path are not trusted, and never expose Sunshine directly to the public Internet.

A paired Moonlight client can inject keyboard and pointer input into the GNOME session. Pair only devices and users you trust; separate Sunshine state does not provide separate desktop input seats.
