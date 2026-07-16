#!/usr/bin/env bash
set -uo pipefail

failures=0

check() {
  local label=$1
  shift
  if "$@" >/dev/null 2>&1; then
    printf 'ok   %s\n' "$label"
  else
    printf 'FAIL %s\n' "$label"
    failures=$((failures + 1))
  fi
}

check "Wayland session" test "${XDG_SESSION_TYPE:-}" = wayland
check "GNOME Shell" command -v gnome-shell
check "Mutter ScreenCast bus" gdbus introspect --session --dest org.gnome.Mutter.ScreenCast --object-path /org/gnome/Mutter/ScreenCast
check "Mutter DisplayConfig bus" gdbus introspect --session --dest org.gnome.Mutter.DisplayConfig --object-path /org/gnome/Mutter/DisplayConfig
check "GStreamer pipewiresrc" gst-inspect-1.0 pipewiresrc
check "PipeWire" command -v pw-cli
check "Sunshine" command -v sunshine
check "Python GI/GStreamer" python3 -c 'import gi; gi.require_version("Gst", "1.0"); from gi.repository import Gio, GLib, Gst'

features=$(gsettings get org.gnome.mutter experimental-features 2>/dev/null || true)
if [[ $features == *scale-monitor-framebuffer* ]]; then
  printf 'ok   Mutter fractional scaling\n'
else
  printf 'warn Mutter fractional scaling is not enabled (installer can enable it)\n'
fi

for unit in gnome-virtual-monitor.service app-dev.lizardbyte.app.Sunshine.service app-dev.lizardbyte.app.Sunshine.Android.service; do
  if systemctl --user is-active --quiet "$unit"; then
    printf 'ok   active: %s\n' "$unit"
  else
    printf 'warn inactive: %s\n' "$unit"
  fi
done

exit "$failures"
