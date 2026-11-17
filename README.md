# London CANOPY 8 km optimised viewer

[Open the London viewer](https://srst-by722.github.io/canopy-saved-walks/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&walkrun=1).

Independent deployment on BoHan Ye’s account, derived from [Sam’s canopy-saved-walks](https://github.com/dodgykid101/canopy-saved-walks). The 17 November 2026 health update integrates the public viewer and saved results at `f6e341b80e8280c6a2cb3af37879bd87a541f862` while preserving the London optimisation: fast pedestrian startup, Bristol-style directional wind streaks, and on-demand sunlight/flood loading.

There are 15 journeys with four saved variants each: walking or running, in June or December. The update includes shared scenario time, sunlight and thermal-comfort plots, personal-reference breathing contributions, and modelled waits for pedestrian signals and gaps in saved cars. The browser replays saved outputs; it does not run the planner or breathing model live. These are illustrative research scenarios, not validated health advice or real-world crossing guidance. Running-specific breathing is not calibrated.

Geometry and original physical-field/traffic files are preserved. The separate traffic-audit and underground candidate is not part of this health release. See [JOURNEYS.md](JOURNEYS.md), [UPSTREAM_README.md](UPSTREAM_README.md), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Sam’s local solver source and private-input setup remain available in the upstream `local-source/` directory; no private inputs or live backend are required by this public replay.

Local checks: `node --test tests/*.mjs` and `python3 tools/verify_static.py`. The latter verifies published assets and saved scenario invariants, not clinical or physical validity. Pages is served from this repository’s `london-optimised` branch.
