# Architecture

## Virtual output lifecycle

1. Read `DisplayConfig.GetCurrentState`, require logical layout mode, capture all active logical groups with exact current mode IDs, and snapshot pre-existing virtual connectors. Legacy mode instead validates the configured primary mode.
2. Create one Mutter ScreenCast session.
3. Call `RecordVirtual` once per configured virtual monitor before starting the session.
4. Listen for each stream's `PipeWireStreamAdded` node ID.
5. Start a dedicated `pipewiresrc -> queue -> fakesink` pipeline per node with fixed width, height and maximum refresh.
6. Wait for all matching virtual modes to appear in `DisplayConfig.GetCurrentState`.
7. Select the nearest supported per-output scales.
8. Compute virtual positions relative to the preserved physical anchor, retaining physical groups and transforms. Translate the whole desktop only if negative coordinates require it, verify the complete layout, then apply it temporarily.
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
composition functions. `LogicalMonitor` retains the grouping of one or more
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
