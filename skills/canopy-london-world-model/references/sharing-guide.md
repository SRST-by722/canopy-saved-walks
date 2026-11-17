# Technical walkthrough for Prof. Li's team

The demonstration illustrates how to assemble geographically aligned city geometry, recorded physical fields and agents into a reusable browser scene. The working example is the London Imperial Corridor, with a separate conceptual indoor preview.

## Suggested sequence

1. Open the walking link and show complete geometry and lightweight geometry. Explain the common coordinate frame and separate representations for overview, near detail and low-memory devices.
2. Open the scene descriptor and follow its model path, detail index, masks and field transport entries. Show how data/configuration drives a shared viewer.
3. Show wind streaks over the speed map. Explain the fixed final vector snapshot, component decoding, coordinate conversion and visual time scaling.
4. Show summer irradiance and winter shadows. Explain precomputed data, on-demand frames and independent recorded timestamps.
5. Demonstrate saved-route playback. Explain which functions come from the existing CANOPY scene and which browser loading changes were added in this optimisation.
6. Open this skill and its implementation/source map. Show the inspect script, reproduction command and owned GitHub Pages deployment.
7. For a Singapore adaptation, establish geography/height/terrain availability, desired fields, solver inputs and the target device before choosing fidelity and download budgets.

## Questions the workflow can answer

- Where does each displayed component come from?
- Which data have been measured, simulated, inferred or resampled?
- Which coordinate transform and clock connect a component to the scene?
- What can be reused for another city, and which inputs or simulations need regenerating?
- How are the browser package, source provenance and numerical outputs versioned?
- What was actually tested on a physical device?

## Optional indoor example

[White City conceptual indoor preview](https://srst-by722.github.io/white-city-indoor-preview/) demonstrates an authored single floor with plan, overview and interior walk controls. Rooms, dimensions and furniture are assumed; the building identity and actual floor plan remain unverified. It is a procedural-generation illustration separate from the London outdoor dataset.

## Scope of this release

The team's existing CANOPY work supplies London geometry and recorded numerical/agent data. BoHan's contribution in this release is the viewer optimisation, directional wind presentation and independently hosted integration. New traffic validation, underground integration and current upstream changes should be discussed as ongoing work until their outputs are checked.
