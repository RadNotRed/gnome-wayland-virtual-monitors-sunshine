#!/usr/bin/env bash
set -euo pipefail

unit_dir="$HOME/.config/systemd/user"
sunshine_dropin_dir="$unit_dir/app-dev.lizardbyte.app.Sunshine.service.d"
state_dir="$HOME/.local/state/gnome-wayland-virtual-monitors-sunshine"
feature_marker="$state_dir/added-scale-monitor-framebuffer"
legacy_snapshot="$state_dir/original-experimental-features"

systemctl --user disable --now gnome-virtual-monitor.service 2>/dev/null || true
remove_feature=false
if [[ -f "$feature_marker" ]]; then
  remove_feature=true
elif [[ -f "$legacy_snapshot" ]]; then
  if python3 - "$(<"$legacy_snapshot")" <<'PY'
import ast
import sys

features = ast.literal_eval(sys.argv[1].replace('@as ', ''))
raise SystemExit(0 if 'scale-monitor-framebuffer' not in features else 1)
PY
  then
    remove_feature=true
  fi
fi

if [[ $remove_feature == true ]]; then
  current=$(gsettings get org.gnome.mutter experimental-features)
  updated=$(python3 - "$current" <<'PY'
import ast
import sys

features = ast.literal_eval(sys.argv[1].replace('@as ', ''))
features = [item for item in features if item != 'scale-monitor-framebuffer']
print(repr(features))
PY
  )
  gsettings set org.gnome.mutter experimental-features "$updated"
fi
rm -f "$feature_marker" "$legacy_snapshot"

rm -f "$unit_dir/gnome-virtual-monitor.service"
rm -f "$sunshine_dropin_dir/virtual-monitor.conf"
rmdir "$sunshine_dropin_dir" 2>/dev/null || true
rm -rf "$HOME/.local/lib/gnome-wayland-virtual-monitors-sunshine"
systemctl --user daemon-reload

printf 'Code and unit removed. Configuration and all Sunshine state were preserved.\n'
