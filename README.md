# Canopy saved healthy journeys

Open https://dodgykid101.github.io/canopy-saved-walks/ in a current WebGL browser. No Python server or download is needed.

15 individual journeys cover different areas and distances. Each has four precomputed variants: walking at 4.8 km/h or running at 9 km/h, on 21 June or 21 December clear-sky sunlight scenarios. Departure is fixed at 08:50; maximum search duration is 13 hours. Choose a journey, mode and day, then load the saved journey. Arbitrary endpoints and departure times need the private full local solver.

The latest demo includes a shared journey clock for the person, original recorded traffic and environmental playback; smoothly repeating pollution and temperature; full-map field estimates; sunlight plots and thermal comfort; personal-reference breathing contributions under the health score; and waits for modelled pedestrian lights plus gaps in retained cars. Pink route arrows, follow-person playback and hidden sample points are retained. Roads and recorded traffic are unchanged.

The wave planner used candidate-location and arrival-time conditions and crossing waits when generating these results. The browser replays those solved routes; it does not rerun the wave or CVAE. CVAE weights and recorded activity inputs are unchanged. Running-specific breathing is not calibrated. Health is an experimental index, not clinical advice. Solar warming and missing-cell filling are illustrative; recorded traffic gap checks are not real-world safety assurance. Route search is bounded.

Only derived saved results and public viewer assets are published. Participant histories, baseline source files, model checkpoints, Python runtime and the live solver are excluded. Full local software is distributed separately in a private repository.

Validation: node --test tests/*.mjs; python tools/verify_static.py. GitHub Actions builds the allowlisted Pages artifact with tools/prepare_pages.py.

## Full local app source

The current local Python solver and setup instructions are in [local-source](local-source/README.md). Private participant/model inputs are excluded. This does not change the public demo link; no new release is needed.
