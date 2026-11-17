---
name: canopy-london-world-model
description: Build, inspect, optimise and deploy a CANOPY urban world model viewer using the London Imperial Corridor reference. Covers scene and asset contracts, geometry, recorded physics fields, traffic and pedestrian replay, directional wind visualisation, progressive loading and GitHub Pages delivery.
---

# CANOPY London world model

Use the London reference to integrate a geographically aligned scene, recorded simulation outputs and browser interactions. Preserve provenance for geometry, simulations and modifications. Make the desired city, area, inputs and output explicit before adapting this workflow.

The shareable reference is BoHan Ye's optimised deployment of CANOPY, derived from the team's London scene and saved-walk viewer. Its published snapshot is pinned in [implementation.md](references/implementation.md). This package documents the browser integration and a method for constructing another scene. Reproducing the original numerical simulations additionally requires their upstream pipelines, input configurations, environments and model weights.

## Choose the entry point

- For a presentation or technical walkthrough, read [sharing-guide.md](references/sharing-guide.md).
- For source navigation and component ownership, read [implementation.md](references/implementation.md).
- For a new geographical scene or field integration, read [scene-contract.md](references/scene-contract.md).
- For loading, wind streaks and device adaptation, read [performance.md](references/performance.md).
- For local reproduction, verification and publication, read [delivery.md](references/delivery.md).
- For the current scope and acceptance limits, read [evidence.md](references/evidence.md).

## Working sequence

1. Establish the source repository, exact commit and actual Pages source branch. Read the scene descriptor, transport metadata and provenance before changing code. A repository's default branch can differ from its deployed branch.
2. Trace a feature from its scene key through its active loader to its data files and UI. A module present on disk may be inactive in the selected scene.
3. Define the geographic coordinate frame, vertical reference, array axis order, units, masks and separate layer clocks. Verify these with known points before visual tuning.
4. Prepare geometry and field web representations with recorded conversion steps. Preserve source assets and distinguish source resolution from display resolution.
5. Make the primary interaction available early, then load detail near the camera and fields when selected. Keep explicit quality controls available.
6. Verify visible behaviour, numerical decoding, coordinates and resource requests. Record the actual device, network and cache state when measuring performance.
7. Publish only the intended site and supporting skill to the authorised destination. Retain source credits. Verify the hosted URL in an anonymous browser and provide exact limitations alongside the result.

For the supplied London checkout, run the bundled checker without installing dependencies.

```sh
python3 skills/canopy-london-world-model/scripts/inspect_site.py .
```

To use this skill in another agent, copy this entire directory into that agent's skill directory and invoke `$canopy-london-world-model`. The references also work as standalone Markdown reading material.
