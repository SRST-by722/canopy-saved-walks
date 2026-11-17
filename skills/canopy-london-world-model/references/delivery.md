# Reproduction and deployment

## Reproduce the pinned viewer

Requires Git and Python 3. The runtime is a static site with vendored Three.js. No GPU simulation run is needed to replay these published outputs.

```sh
git clone --branch london-optimised --single-branch https://github.com/SRST-by722/canopy-saved-walks.git london-canopy
cd london-canopy
git rev-parse HEAD
python3 skills/canopy-london-world-model/scripts/inspect_site.py .
python3 -m http.server 8802 --bind 127.0.0.1
```

Open the full path to start streaming the walking scene.

```text
http://127.0.0.1:8802/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&walkrun=1
```

The service worker decompresses requested GLBs from .glb.gz assets. Serve through localhost or HTTPS and retain `viewer/pages-bootstrap.js`, `asset-router.js`, routing metadata and vendored dependencies. Opening index.html directly as a file does not reproduce this transport.

To reproduce exactly the original deployed runtime, check out `871c0171fe779e0391824358f7c4e719a690636e`. The skill was added later, so keep a copy of the checker outside the checkout when moving to that commit.

## Acceptance sequence

1. Verify every download-manifest entry's bytes and SHA-256.
2. Confirm Automatic, forced lightweight and forced complete modes.
3. Test saved route selection, Play/Pause, seek and arrival. Record the final detail tile/asset count.
4. Toggle wind streaks while retaining the speed field, check direction and fixed-snapshot label.
5. Play summer irradiance and winter shadows. Check first-frame requests, dates, clock progression and memory retention.
6. Check flood and tracer decoding and their independent clocks.
7. Record requested asset origins and any 404s or browser exceptions.
8. Repeat the critical path on the actual presentation device. Document any untested devices.

## Publish from an owned fork

Read the repository's existing Pages source first. Preserve licences and source credits. For this repository the deployment branch is `london-optimised`; the fork's `main` tracks a separate source snapshot.

Commit the reviewed files, push that branch and inspect the Pages build. New repositories can enable branch deployment with:

```sh
gh api -X POST repos/OWNER/REPOSITORY/pages   -f 'source[branch]=DEPLOY_BRANCH' -f 'source[path]=/'
```

Use the existing configuration for an already configured site. Wait for successful deployment, then anonymously fetch the viewer, updated scripts, descriptor and a compressed geometry asset. Compare hashes with the reviewed files. Finish with actual hosted-browser interaction checks.

Changes to download-managed runtime files require refreshing their size/hash entries and using an appropriate cache version. Supporting skill documentation is outside the runtime download manifest.

For contributions to the team's reorganised CANOPY repository, confirm the current integration repository and branch and submit a focused PR there. A successful fork deployment alone does not establish upstream integration.

## Published demonstration links

- [Walking and city](https://srst-by722.github.io/canopy-saved-walks/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&walkrun=1)
- [Lightweight walking](https://srst-by722.github.io/canopy-saved-walks/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&walkrun=1&lite=1)
- [Wind](https://srst-by722.github.io/canopy-saved-walks/viewer/3d/?scene=imperial_corridor_8km&pose=overhead&phase=wind&mode=seq)
- [Sunlight](https://srst-by722.github.io/canopy-saved-walks/viewer/3d/?scene=imperial_corridor_8km&pose=overhead&phase=solar&mode=seq)
