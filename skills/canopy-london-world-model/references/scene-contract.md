# Constructing a geographically aligned scene

## Inputs and build stages

For a new city, establish an area of interest and projected metric CRS, building footprints and IDs, height evidence, terrain, road network and relevant field inputs. Record dataset dates, licences, coverage gaps and transformations. Retain measured, tagged and inferred heights separately. Where terrain or heights are unavailable, record the adopted approximation.

Create editable source geometry first, followed by browser GLBs. Partition large scenes into a coarse overview and spatial detail tiles. Keep stable feature IDs between representations so selection and metadata remain attached to the same building. The London runtime is a reference for this packaging. It does not bundle every original geometry generation or numerical simulation dependency.

To regenerate physics, obtain the upstream solver, configuration, weights and environment, then produce arrays with explicit shape, units, mask and time metadata. Export browser representations separately. To adapt existing results, validate compatibility with the new geometry before using them as evidence.

## Spatial convention

The reference scene uses a local east/north frame in metres and a Three.js Y-up display. East maps to X, height to Y and north to negative Z. Base extent is 8,192 × 8,192 m, with X west boundary −4,096 m and Z south boundary +4,096 m. Base grid is 1,024 × 1,024 at 8 m.

For cell-centred field samples with cell width d, column c and row r,

```text
X = -4096 + (c + 0.5) * d
Z =  4096 - (r + 0.5) * d
```

Derive the number of rows and columns from each field's own cell size. Rows increase northwards from the south edge. Check a known building, road junction and domain corner across geometry, masks, traffic and field overlays.

The London scene is terrain-normalised and projected onto a flat plane. Its context metadata explicitly says bridge deck elevations are not represented. Ground colouring can show terrain elevation without making the ground geometrically elevated.

## Field representation and clocks

Read `protocol_display.npy_transport`, `preview_fields_8m`, `wind_history`, the physics manifest and compact provenance together. Original-source resolution, stored web resolution and render sampling may differ.

- Wind streaks use the final snapshot at model t = 7,500 s, nominal height 6 m, shape [1, 3, 2048, 2048], 4 m cells. Components 0 and 1 are east/north.
- The wind speed background uses `wind_history`, which replaces the scene's wind display layer during boot. It contains magnitude frames with its own sampling metadata.
- Summer sunlight has 99 samples and winter sunlight 47. Summer/winter dates are 21 June and 21 December 2026, at ten-minute sampling in the descriptor.
- The road tracer has 21 samples at 30 s intervals and arbitrary units. The descriptor describes uniform sources on mapped road cells.
- Flood preview has 100 retained samples from 181 source frames. Use `time_s` and `source_indices`; its timestamps are uneven.
- Temperature metadata describes a 32 m grid with 11 samples; London hides temperature through its context config.
- Traffic retains recorded sample times. The 17 November saved-journey integration maps journey elapsed time onto a shared scenario clock; verify play and seek against both the route panel and traffic. Other physics timelines retain their source-specific time semantics.

The 8 m previews include valid-cell 2 × 2 averaging and float16 storage. Several transport arrays use 8-bit quantisation, decoded with `offset + code * scale` and an invalid code. Gzip preserves the stored bytes but does not undo prior averaging or quantisation. Historical source descriptions saying lossless transport must be interpreted at this storage stage.

## Traffic and pedestrians

London's active context points to `context/traffic-am.json` and `context/traffic-am.bin`. Read this metadata and `corridor-context.js` before interpreting the binary. The generic `traffic.js` uses a different six-int16 record contract and should not be applied to the London context binary by assumption.

For traffic changes, check record counts, IDs, timestamps, coordinate origin, yaw, driving side, lane association and junction behaviour. For pedestrian coupling, test crossing waits against the same replay clock. Check train motion, station positions and timing explicitly when adding underground transport.

Regenerating a road-source tracer from actual vehicle emissions requires an emissions mapping and an agreed traffic export. Existing road-cell tracer output does not establish per-vehicle attribution.
