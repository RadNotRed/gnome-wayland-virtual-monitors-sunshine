# Architecture

## Virtual output lifecycle

1. Create one Mutter ScreenCast session.
2. Call `RecordVirtual` once per configured virtual monitor before starting the session.
3. Listen for each stream's `PipeWireStreamAdded` node ID.
4. Start a dedicated `pipewiresrc -> queue -> fakesink` pipeline per node with fixed width, height and maximum refresh.
5. Wait for all matching virtual modes to appear in `DisplayConfig.GetCurrentState`.
6. Select the requested physical refresh and the nearest supported per-output scales.
7. Compute relative logical positions, normalize them to non-negative coordinates, verify the complete layout, then apply it temporarily.
8. Publish a readiness marker in `$XDG_RUNTIME_DIR` so dependent Sunshine services start only after the layout is usable.

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
