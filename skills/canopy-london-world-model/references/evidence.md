# Evidence and current limits

Snapshot reviewed on 17 November 2026. Runtime commit 871c0171fe779e0391824358f7c4e719a690636e was confirmed as the successful Pages build.

## Recorded tests

The 16 November local Mini Safari 27.2 review observed walking controls by 13.1 s and completed the default 671 m route. The final scene reported 64 tiles and 331 geometry assets. Later checks on the independently unpacked localhost package verified lightweight wind tails, tail toggling, summer irradiance playback and winter shadows.

A same-environment headless Chromium comparison recorded desktop route-menu readiness 29.2 → 22.1 s and transferred bytes before that point 55.5 → 20.2 MB. A simulated Pixel 7 configuration recorded Play walk readiness 32.8 → 14.4 s and bytes 42.1 → 12.3 MB. These are single-run, software-rendered results, with device emulation rather than physical-phone testing.

The public deployment checks confirmed successful Pages build, byte equality of viewer/index, main.js, wind-trails.mjs, asset-router.js and download manifest, plus compressed-road HTTP access. Complete hosted-route replay was not repeated in those checks. Physical phones, Air and slow networks remain unverified in this evidence set.

## Scientific and integration limits

The scene descriptor characterises the wind as SCALED rollout without a CFD reference; temperature as controlled scenario output; solar as clear-sky building-based estimates; tracer as arbitrary road-cell sources; flood as a prescribed storm. Browser acceptance does not validate those physical models.

Traffic demand and replay need the additional checks requested on 17 November. Underground demonstration remains separate integration work. The 17 November health update passed 21 Node tests and the static verifier (60 variants, 1,480 protected CANOPY asset hashes unchanged). Mini Safari locally loaded full geometry, switched walking/running and June/December, played and sought the shared clock, and displayed winter sunlight and Bristol-style wind streaks. Console error totals and FPS were not measured for this health review. These checks do not validate the health model; running breathing is uncalibrated. Available module files alone cannot establish completion. Later collaborator reports must be checked against the deployed commit.

## Provenance trail

Use repository THIRD_PARTY_NOTICES.md and UPSTREAM_README.md, the scene descriptor, compact-provenance reports and per-asset provenance files. Retain these when adapting the package. The public skill excludes private correspondence and local workstation paths.

A complete scientific rerun requires recovering each original input, executable version, weights, boundary conditions, seed, environment and output manifest. The provided static-site checker verifies the published replay assets only.
