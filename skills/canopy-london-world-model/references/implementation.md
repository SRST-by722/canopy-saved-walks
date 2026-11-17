# Source map and component responsibilities

## Pinned reference

- Deployment repository [SRST-by722/canopy-saved-walks](https://github.com/SRST-by722/canopy-saved-walks).
- Pages source branch `london-optimised`.
- Runtime baseline commit `871c0171fe779e0391824358f7c4e719a690636e`.
- Health replay source updated on 17 November to `dodgykid101/canopy-saved-walks` at `f6e341b80e8280c6a2cb3af37879bd87a541f862`.
- Scene ID `imperial_corridor_8km`. The actual square is 8,192 m per side.
- The optimised runtime manifest contains 1,632 assets totalling 496,903,865 bytes. Supporting documentation is outside that download manifest.

Paths below are relative to repository root.

| Component | Source entry | Role and dependency |
| --- | --- | --- |
| Boot and asset transport | `viewer/pages-bootstrap.js`, `asset-router.js` | Registers the service worker, serves compressed GLB requests, supports complete offline caches |
| Scene discovery | `scenes/index.json`, `viewer/scene.js` | Selects the descriptor and resolves repository-relative resource URLs |
| Scene contract | `scenes/imperial_corridor_8km/scene.json` | Geometry, field grids, masks, clocks, focus and feature availability |
| Main renderer | `viewer/3d/main.js`, `index.html` | Three.js scene, camera, phase controls, asynchronous layer activation |
| Complete city | `viewer/model-source.js`, `viewer/3d/complete-detail-tiles.js` | Base GLB and nearby detail tiles |
| Lightweight city | `viewer/3d/proxy.js` | Extruded building proxy from footprint and height masks |
| Geography context | `viewer/3d/corridor-context.js`, `corridor-terrain.js` | Road surfaces, landscape and the selected London traffic subset on the flat scene plane |
| Fields | `viewer/npy.js`, `frames.js`, `recorded-clock.mjs` | Array decoding, frame transport and recorded sample times |
| Wind streaks | `viewer/3d/wind-trails.mjs` | Animated short tails sampling fixed final horizontal velocity |
| Walking | `viewer/3d/pedestrian/saved-journeys.mjs`, `canopy-pedestrian.mjs`, `follow-walker.mjs` | Saved route selection, pedestrian and follow camera |
| Route scores | `viewer/3d/pedestrian/corridor-health-score.mjs`, `imperial-route-plots.mjs` | Route display and experimental health-related outputs |
| Generic traffic | `viewer/3d/traffic.js` | Optional scene traffic replay loader, activated by a matching scene config |
| Generic public transport | `viewer/3d/transport.js` | TfL network/stop display and optional online arrivals when configured |
| UAV | `viewer/3d/uav-layer.js`, `wind-uav-route.mjs` | Configured UAV route visualisation, with `assets/uav-wavepde-20261111/config.json` |
| Packaging | `download-manifest.json`, `asset-routes.json` | Download sizes, SHA-256 hashes and asset routing |

## Contributions in this London release

The upstream project supplies the city geometry, physics outputs, recorded traffic, saved routes and most viewer components. BoHan's optimisation candidate changes four runtime files.

- `main.js` makes pedestrian controls available earlier, schedules background work, integrates wind streaks and bounds decoded sunlight/flood frame retention.
- `wind-trails.mjs` adds Bristol-style directional tails using London's existing velocity components.
- `complete-detail-tiles.js` prioritises detail near the camera target.
- `pedestrian/saved-journeys.mjs` shares cached promises for route catalogue and metadata requests.

The download manifest was refreshed accordingly. This release reused the supplied geometry and numerical results.

## Active feature checks

London uses `corridor_context.traffic_meta` and `traffic_binary`. Its top-level `traffic` and `transport` entries are absent. Therefore the generic traffic and TfL loaders alone cannot establish which features London exposes. The descriptor also sets `corridor_context.temperature_hidden=true`; temperature arrays exist, but their presence does not prove a visible temperature tab.

For work after this snapshot, compare upstream changes before rebasing. A current online report from a collaborator can describe a newer branch than this deployed snapshot.

## Health integration, 17 November

Fifteen journeys now have walking/running and June/December variants (60 saved files). `journey-clock.mjs` and `shared-environment.mjs` map journey progress to the shared scenario and traffic clock. `solar-environment.mjs` supplies date-specific sunlight. Catalogue and metadata reads bypass the offline asset cache with `cache: no-store`, while shared promises avoid duplicate requests. Geometry and original physical-field/traffic bytes are unchanged. Local solver source remains upstream; the deployed viewer replays saved outputs.
