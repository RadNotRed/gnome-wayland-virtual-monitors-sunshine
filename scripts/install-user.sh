#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
lib_dir="$HOME/.local/lib/gnome-wayland-virtual-monitors-sunshine"
config_dir="$HOME/.config/gnome-virtual-monitors"
unit_dir="$HOME/.config/systemd/user"
state_dir="$HOME/.local/state/gnome-wayland-virtual-monitors-sunshine"
feature_marker="$state_dir/added-scale-monitor-framebuffer"

install -d -m 755 "$lib_dir" "$config_dir" "$unit_dir"
install -d -m 700 "$state_dir"

cp -aT "$root/src/gnome_virtual_monitors" "$lib_dir/gnome_virtual_monitors"
install -m 644 "$root/systemd/gnome-virtual-monitor.service" "$unit_dir/gnome-virtual-monitor.service"

if [[ ! -e "$config_dir/config.toml" ]]; then
  install -m 600 "$root/config/three-monitors.example.toml" "$config_dir/config.toml"
fi

current=$(gsettings get org.gnome.mutter experimental-features)
updated=$(python3 - "$current" <<'PY'
import ast
import sys

features = ast.literal_eval(sys.argv[1].replace('@as ', ''))
if 'scale-monitor-framebuffer' not in features:
    features.append('scale-monitor-framebuffer')
print(repr(features))
PY
)
gsettings set org.gnome.mutter experimental-features "$updated"
if [[ $updated != "$current" && ! -e "$feature_marker" ]]; then
  install -m 600 /dev/null "$feature_marker"
fi
systemctl --user daemon-reload

printf 'Installed. Edit %s, validate it, then enable the service.\n' "$config_dir/config.toml"
