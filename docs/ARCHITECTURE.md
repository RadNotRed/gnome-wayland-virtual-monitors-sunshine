# Architecture

## Virtual output lifecycle

1. Read `DisplayConfig.GetCurrentState`, require logical layout mode, capture all active logical groups with exact current mode IDs, and snapshot pre-existing virtual connectors. Legacy mode instead validates the configured primary mode.
2. Create one Mutter ScreenCast session.
3. Call `RecordVirtual` once per configured virtual monitor before starting the session.
4. Listen for each stream's `PipeWireStreamAdded` node ID.
5. Start a dedicated `pipewiresrc -> queue -> fakesink` pipeline per node with fixed width, height and maximum refresh.
6. Wait for all matching virtual modes to appear in `DisplayConfig.GetCurrentState`.
7. Select the nearest supported per-output scales.
8. Restore a saved layout when explicitly enabled and available; otherwise compute virtual positions relative to the preserved physical anchor, retaining physical groups and transforms. Translate the whole desktop only if negative coordinates require it, verify the complete layout, then apply it temporarily.
9. Publish a readiness marker in `$XDG_RUNTIME_DIR` so dependent Sunshine services start only after the layout is usable.

The fakesink pipelines only negotiate and keep the Mutter outputs alive. Sunshine opens separate XDG Portal/PipeWire sessions to capture them.

## Role mapping

The daemon does not rely on `Meta-0` or `Meta-1` as durable identities. It snapshots pre-existing virtual connectors before creating its session and then matches each newly created output by its configured resolution. The configuration loader therefore requires every virtual monitor to have a unique width/height pair.

## Multiple Sunshine instances

Sunshine's selected output is global to a process. The second instance uses:

- a distinct systemd app unit and therefore a distinct Portal app ID;
- a distinct `XDG_CONFIG_HOME` and `portal_token`;
- a different base port and complete port family;
- separate pairing state, certificates, Web UI credentials and logs.

Both streams still belong to the same GNOME desktop and input seat.

## Readiness and failure behavior

The daemon removes any stale readiness marker before creating outputs and writes it only after `ApplyMonitorsConfig` succeeds. The Android unit waits for that marker instead of sleeping for a fixed interval and binds its lifetime to the virtual-monitor service. Stopping or losing the Mutter session removes the outputs; saved Portal tokens may then need renewal because they identify the old capture source.

## Physical state composition

`display_state.py` contains pure capture, role resolution, mode validation and
composition functions. All three paths (preserved, saved and legacy) produce the
same `LogicalMonitor` model. The daemon separates layout construction from D-Bus
verification/application; readiness and logging follow successful application.
The CLI uses the daemon's public `save_layout()` operation without starting a session. `LogicalMonitor` retains the grouping of one or more
`MonitorMode` outputs, each with its connector and exact selected mode ID, pixel
size and unrounded refresh. Rotation comes from Mutter's transform, never from
aspect ratio. The anchor's logical dimensions account for both scale and transform.

Snapshots are taken before `RecordVirtual`; retries do not replace that snapshot
with Mutter's temporary automatically rearranged layout. Missing connectors,
changed modes or unsupported scales fail before applying. Virtual candidates must
be new since preflight, classified as virtual, and uniquely match the configured
resolution. A physical output with the same size is never a candidate. Ambiguity
fails explicitly. `Meta-*` is only a transient classification/lookup aid.

The original one-primary path remains explicitly selectable. The preservation
path retains pre-existing virtual groups too, avoiding disruption to other
sessions. Dynamic hotplug during startup requires restarting with a stable topology.

## Saved layouts

`saved_layout.py` is separate from physical preservation. `--save-layout` reads
current state without starting/stopping a ScreenCast session or changing the
ready marker. It resolves configured virtual roles by unique resolution, then
serializes every active logical group. Unconfigured active virtual outputs,
inactive configured roles and ambiguous candidates cannot be saved safely.

Version 1 JSON records role definitions (name, configured resolution and refresh),
physical connector/mode IDs, virtual role identities, actual mode dimensions and
refresh, and logical X/Y, scale, transform and primary status. Virtual connector
names and mode IDs are intentionally omitted. Files are written atomically with
0600 permissions under the user's XDG state directory; no repository-local state
or dependencies are needed. The installer copies the module with the package.

With `restore_saved_layout = true`, preflight reads and validates state before
creating outputs. The normal lifecycle still creates streams and waits for new
modes. Role resolution excludes pre-existing virtual connectors. Restore remaps
each role to its new connector/mode, validates physical connectors and exact mode
IDs, requires matching dimensions/refresh and supported saved scales, then verifies
and temporarily applies the complete layout. Saved role definitions must match
configuration. An active output absent from the save is an error, not disabled.
Readiness is published only after this final layout succeeds, so dependent
Sunshine services cannot start on the intermediate automatically assigned layout.

No file falls back to configured relative placement. Invalid/incompatible state
fails startup explicitly. Saving is manual; shutdown never overwrites a desired
layout with a transient or physical-only arrangement. Restoration does not manage
Portal tokens, hardware hotplug policy, GNOME monitors.xml, or client input seats.
Physical connector moves and unsupported saved modes require a new save.
