# CANOPY + pedestrian model — 11 November 2026

This separate working copy integrates the pedestrian/CVAE work into the supplied
`canopy-codex-github-pages` download. The original Canopy folder and the older viewer
on port 8810 are unchanged. Nothing was committed, sent or published.

## Open

Run `Start-Canopy-Pedestrian.cmd`, then open:

http://127.0.0.1:8811/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&walkrun=1

The **Walking** tab opens/closes the left sidebar. Choose **Pick start** and
**Pick destination**, click mapped paths, then **Calculate wave route**. Scroll below
the plots for **Play walk**, speed, scrubber, focus and top-down/3D controls. Walking
has its own clock; Canopy's recorded traffic controls and physics clocks remain separate.

The launcher uses the existing sibling Imperial Python environment on this machine.
Elsewhere install Python 3.11+ with NumPy, pandas, PyTorch and Pillow, and configure
the model files locally. Shapely is only needed to rebuild the walking graph; a local
copy is in `pedestrian/dependencies`. No browser can run the CVAE without this local API.

## Preserved Canopy content

Original road lanes, connections, terrain, detailed buildings, native signal placements,
vehicle replay, scene configuration and physical fields are unchanged. Only the original
`viewer/3d/main.js`, `asset-router.js` and `download-manifest.json` are adapted:

- Viewer: optional pedestrian widget registration; walking can open without waiting for
  unrelated field preparation. Existing native mode controls remain available.
- Asset router: uses a local original asset when present before the existing remote gateway.
- Download manifest: updated public frontend hashes and new pedestrian frontend files.

The provided download lacked some files and its gateway returned HTTP 403. Missing
assets were restored from the official upstream releases, **only when their bytes
matched the existing Canopy manifest's SHA-256**. These include the unchanged 600-frame
traffic replay and original physical fields. The source download's 884 file hashes are
retained in `pedestrian/original-canopy-hashes.json`. Run the preservation check below.

## Walking network and lights

The 70,076 native vehicle lanes deliberately omit pedestrian-only lanes. The new overlay
is independently derived from **Canopy's own** landscape source's mapped footways, paths,
pedestrian streets and steps. It does not use the old Imperial `network.json`, invent
pavements along vehicle roads, copy the old environmental exclusions or alter vehicle lanes.

The generated overlay has 38,845 nodes, 41,252 undirected links and 1,998 connected
components; the largest has 25,541 nodes. Zero links are excluded by environmental masks.
Intersections are geometrically noded within a level, not surveyed accessibility. No
proximity links bridge disconnected gaps. Access permissions absent from the map are not
claimed verified. Steps are mapped paths; walking speed/cost has no incline component.

The first connectivity repair retained 341 mapped sections shorter than 10 cm, which the initial
builder discarded after road-envelope splitting. This reconnects 68 formerly separate
components while retaining all 38,378 previous links; it does not add proximity bridges.
During destination picking, mint paths are connected to START and grey paths are not.
A disconnected click keeps the existing destination and explains how to choose again;
it never silently substitutes a nearby connected path. A new start in another component
prompts a new destination before calculation. `pedestrian/cache/connectivity-repair.json`
records the before/after comparison and a previously disconnected junction's API replay.

The second repair correctly interprets Canopy's `covered` arrays as **segment indices**.
The original viewer skips those segments when drawing paths; the first importer incorrectly
treated the array as a flag for the entire path. Now 751 visible runs from 439 partly hidden
paths are restored (26.35 km of source geometry), while 2,459 explicitly hidden segments
remain excluded. These visible runs join the ordinary ground-level network normally.
Modelled pedestrian lights are assigned where restored paths cross visible mapped roads.

The planner supports one edge per node pair. To preserve distinct parallel walking paths,
145 alternatives receive an intermediate routing node on their existing geometry; no new
shortcut is drawn, and crossing edges are kept intact so no new waiting point is introduced
inside a crossing. This also fixes the loss of a previously usable 25.77 m curved path.
Total walking-edge length grows from 922.17 km to 958.11 km; the main connected component
grows from 670.12 km to 694.82 km. Seventy-five previously separate components are joined.
The overall component count rises because some restored outdoor fragments remain isolated
by hidden sections or missing source links; that count alone does not measure coverage.
`pedestrian/cache/visible-segments-repair.json` records lengths, geometric preservation
and successful API replays. `pedestrian/audit_visible_segments.py` reproduces the comparison.

Supported elevated walking sections use Canopy's native bridge-lane elevations within
12 m at the same mapped level. There are 31 such sections. Four bridge entrances now join
ground paths at **exact shared source endpoints** where native deck and terrain heights
agree within 10 cm; only the overlay endpoint height is reconciled. Crossing interiors,
nearby unconnected paths, and endpoints with larger vertical separation are not joined.
The overlay still excludes 326 sections with unresolved elevated geometry, negative-level
sections and explicitly hidden segments. Original Canopy geometry remains intact.

Mapped transverse path/road overlaps are split into 8,278 crossing sections. Each has
our modelled pedestrian red/green/clearance programme. No native pedestrian timing exists
in this download. These added lights are **independent pedestrian scenario lights**, not
the 1,801 original static traffic-signal displays. They do not control the saved cars.
Recorded cars may pass during a modelled WALK phase: this is not a coupled traffic-safety
simulation. Native traffic, its own clock, its signal geometry and trajectories are preserved.

## Your features

The tab and panel are titled **Healthy route recommendation**. Start time defaults to
0 seconds, with Maximum journey duration set to the model's full remaining coverage
(13 hours at start time 0). If maximum is selected, changing start time keeps the selection
at the new maximum; a manually chosen shorter duration is preserved when it still fits.

**Follow walker** starts enabled once a route is calculated. It centres the camera on the
walker and follows movement, waits and timeline scrubbing while preserving the viewing
offset. Manual map interaction, endpoint picking or **Show whole route** disables following;
Checking Follow walker resumes it. Every successful route calculation also checks it again
and centres the camera on the new starting point. Top-down / 3D works in follow mode as well.
Playback defaults to **1× (real time)**, with 0.25× and 0.5× slow motion available. The
model's physical walking speed remains 4/3 m/s (4.8 km/h); 60× playback advances a minute
of model time each real second, rather than changing route physics or breathing inputs.
The speed hint explains the current time multiplier. Optional local `walk-origin`,
`walk-goal`, `walk-start`, `walk-limit` and `walk-elapsed` URL parameters can restore a
paused journey after a UI reload; ordinary launches retain the defaults above.

- Small mint START / purple END flags; sample points hidden until requested.
- One selected pink route, white direction arrows and animated walking person.
- Current-condition health ring /100, followed by selected-route red plots only.
- Dynamic synthetic PM2.5 street colours (6–40 µg/m³, 180-second scenario cycle).
- Existing INH010 CVAE checkpoint, scaler, personal baseline and history; no retraining.
- **Start time** (seconds) and **Maximum journey duration** shown in hours/minutes.
  Maximum is 13 hours at scene start 0, reducing with later starts; default is 30 minutes.
- Separate walk playback speed, pause/seek, camera focus and top-down/3D.
- No Example selector, orange comparison route, cycling mode or incline controls.

Health score:
`100 / (1 + .35 * (.45*(PM/40)^2 + .35*(abs(BR-BR0)/(.25*BR0))^2 + .20*(max(18-T,T-26,0)/10)^2))`.
BR0 is the departure prediction, not a validated healthy baseline. The ring can recover;
elapsed time alone is not a penalty. Tuning is illustrative, not clinical.

## Environmental coverage and physiology

Canopy's native pollution is an arbitrary-unit tracer. It is preserved as its own physics
view, never relabelled as PM2.5. The walking model retains the clearly labelled synthetic
PM2.5 scenario you requested. Walking temperature samples the **native float16 snapshot
at simulation 600 s**, on a 32 m grid, 8 m above ground. It is not a live weather forecast.

Masked temperature stays unavailable in the plot and score; it never removes a mapped
walking link. At those locations the CVAE receives its recorded training-mean temperature,
explicitly labelled imputation. A configurable 3 cost-units/second missing-temperature
penalty prevents an unknown area appearing artificially cooler/healthier during route
selection. It is an availability preference, not a physiological risk estimate. Actual
environmental sampling during movement/waits uses the same native field provider.

Other breathing inputs (humidity/activity/steps/hour features) retain the recorded template.
Breathing updates only at actual five-minute boundaries, including waiting, and is held
between updates. The 2022 historical replay and imputation limitations are inherited.
The history horizon allows selecting a 13-hour journey cap; it does not establish validated
13-hour physiology or guarantee a feasible route. Canopy now uses a destination-guided
bounded wave search. A FIFO graph search first proposes the earliest feasible route with
pedestrian signal waits, and a frozen-environment guide proposes another candidate when
feasible. Each candidate is propagated through the original wave/gate and CVAE cost model.
A wave search then examines their destination corridor (guide cost within 15% plus 30
cost-seconds, plus candidate paths), retaining at most 3,000 additional histories.

If that refinement exhausts its budget, the best fully evaluated candidate remains usable;
it is not reported as a disconnected path or exhausted participant history. This is a
bounded approximation, not the globally health-optimal route. API audits expose the graph
candidate stage, selected route source, search limit and completeness. The viewer reports
when wider search is limited. A genuinely insufficient journey duration has a separate
message; crossing waits and model coverage are still enforced.

Wave scheduling uses an occupied-time-bucket event queue. It preserves distinct histories
and processes short path sections arriving within one bucket. Reaching the history cap
stops new packet emissions but does not discard destination packets already travelling.
Feasible candidate validation is not cut off by the old arbitrary 32,000 health-pseudo-time
horizon; its physical clock must still fit the chosen duration and participant coverage.

## Code and checks

- `pedestrian/build_network.py`: source-only derived graph and geometry provenance.
- `pedestrian/canopy_planner.py`: native graph/temperature providers and retained CVAE planner.
- `pedestrian/health_planning/`: retained wave/state implementation; inexpensive frozen-state
  guidance avoids advancing CVAE for the entire city just to initialise a route search.
- `viewer/3d/pedestrian/`: scoped UI, route/flags, score, plots, walker and pedestrian lights.
- `pedestrian/serve.py`: loopback-only server; private model/history and cache are not served.
- `pedestrian/private/`: local research assets, excluded from source-control/public manifests.
- `pedestrian/health_planning/destination_wave.py`: timed candidate generation, full wave/CVAE
  validation and bounded destination-corridor refinement; feasible incumbent retention.

Checks:

```
python -m unittest discover -s pedestrian/tests -v
node --test pedestrian/tests/test_health_score.mjs pedestrian/tests/test_walking_endpoints.mjs
node --test pedestrian/tests/test_follow_walker.mjs
node pedestrian/test_integration.cjs
python pedestrian/verify_preservation.py
```

The browser test uses this machine's Edge and sibling Puppeteer installation; adjust those
paths elsewhere. It checks score recovery, model updates, stationary waits and WALK entry,
arrival, flags/routes/red plots, point toggling, playback/reset/duration labels, actual map
endpoint picking, independent original traffic and all 331 native geometry assets loading.
It writes `pedestrian/cache/browser-validation.json` and a screenshot. Research outputs are
not clinical validation. The original framework's pre-existing test failures were not changed.

Initial integration validation: 8 Python tests and 3 JavaScript score tests passed. Browser acceptance,
native Wind-to-Walking navigation, endpoint picking and all 331 geometry assets passed.
All 1,562 public asset checksums match the updated manifest; the 884 files in the original
download still match their pre-integration hashes. One concurrent browser startup check
timed out; the isolated full rerun and separate native-view check passed with no page errors.

Connectivity repair validation: 10 Python tests and 5 JavaScript tests passed. A synthetic
5 cm junction remains connected, while a real 1 m gap and an unresolved tunnel remain
separate. The current API routes a formerly disconnected 6.1 cm mapped section. All 1,563
public assets match the refreshed manifest, with original road/traffic/terrain/field assets
unchanged. Browser checks cover default route calculation, destination highlighting and
selection; the user's exact failed endpoint pair was not recoverable from the screenshot.

Second connectivity repair validation: all 13 Python tests pass, including per-segment
visibility, bridge entrance/grade separation and parallel-path preservation. Geometric
comparison finds zero lost length from the previous walking overlay (1 micrometre numerical
tolerance). Live API replays successfully traverse a restored outdoor path in 44.72 seconds
and a newly joined bridge in 79.06 seconds, with CVAE enabled. Original Canopy assets remain
unchanged. Reload the browser to fetch the new network and reachable-path colouring.

History-budget repair: the exact reported endpoint pair from
`pedestrian/cache/history-budget-request.json` now completes in about nine seconds locally.
Its selected route takes 2,418.51 s including 278.64 s of signal waiting, with 10 breathing
profile entries. Wider refinement still reaches 3,000 histories, so this result is the best
tested candidate, not a complete city-wide optimum. The full validated response is retained
privately at `pedestrian/cache/history-budget-fixed-plan.json`. Regression tests cover this
journey, true duration rejection, retained destination packets at the record cap, same-bucket
short segments, and feasible candidates surviving a deliberately tiny refinement budget.
