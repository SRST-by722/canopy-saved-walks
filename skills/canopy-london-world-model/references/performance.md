# Loading and directional wind

## Geometry quality

Without a `lite` URL parameter the menu defaults to Automatic. The code chooses lightweight geometry for phone/tablet user agents, touch-enabled Mac identifiers, or browsers reporting at most 4 GB device memory. Other cases use complete geometry. This is a heuristic. It is not a measured per-device memory budget.

`lite=1` forces the proxy. `lite=0` forces complete geometry. Complete mode continues loading detail after the initial city appears, so record both interactive readiness and complete detail readiness.

## Fast walking entry

With `pedestrian=1`, the default optimised path exposes the city and walking controls as soon as they are ready. UAV routes, transport and road/landscape layers are scheduled in the background. Detail starts near the camera target. Lightweight startup initially loads its footprint and height masks. Saved-route catalogue and metadata requests reuse promises. `fast=0` retains the prior startup route for a controlled comparison.

## Frame loading

After intro completion in sequence mode, the compact path loads sunlight, shadow and flood samples on demand. It retains a bounded decoded window, prefetching 2 samples in lightweight mode and 4 in complete mode, with retention settings of 6 and 12. `compact=all` selects the older full-sequence route for diagnosis.

Treat async state as observable behaviour. Rapidly switch layers or dates, pause, scrub and switch back. Verify that stale requests do not restore a disabled layer. Separate first visit, repeat visit and service-worker-cached timing.

## Wind tails

The loader decompresses the two horizontal components and building mask from the scene's transport descriptors. It validates channel offsets and byte lengths. Sampling is bilinear at cell centres and rejects invalid values and neighbouring solid cells.

Each visible tail advances through the fixed velocity snapshot. East velocity advances world X; north velocity decreases world Z. Tail heads are brighter, colour indicates speed and tail width/visual displacement scale with camera range. The implementation caps the integration display timestep at 0.1 s, uses a 2.2 s particle lifetime, checks the head destination against solids and truncates tails at solid cells. Invalid or slow particles respawn around the camera.

Default count is 4,000 on desktop, capped at 2,500 in lightweight mode. Camera-dependent animation acceleration makes direction readable; playback motion is an illustration of a frozen field. The speed background may continue through a different sequence, so retain the fixed t = 7,500 s label.

Test synthetic eastward and northward vectors, building masks, out-of-domain handling, zero speed, toggling during loading and count changes. Use the module's `audit()` output alongside visual inspection.

## Measuring improvements

Compare the same device, browser, network, cache state, scene and quality setting. Report transferred bytes, main-thread time, interaction readiness, complete geometry readiness, decoded memory, frame rate and errors. A local server versus remote HTTPS comparison cannot isolate code speedup.
