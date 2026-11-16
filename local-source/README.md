# Full local app source — 2026.11.16

This directory contains the current Python solver, local viewer changes, generated walking network, tests and setup files. The repository root remains the public saved-journey demo. GitHub Pages does not publish this directory.

## Setup

Clone or download this entire repository. Use Python 3.12 and a virtual environment:

```powershell
python -m venv local-source/.venv
local-source/.venv/Scripts/python.exe -m pip install -r local-source/requirements-source.txt
local-source/.venv/Scripts/python.exe local-source/prepare_local.py
```

The preparation script checks and reuses the repository's Canopy assets, applying the local viewer overrides into the ignored `local-source/.work/app` directory. It does not replace the web demo. Python dependencies are not bundled here; `requirements-windows-lock.txt` records the portable package's versions. Windows is the tested platform.

Copy the **authorised** `breathing_model` folder from your existing full package into:

`local-source/.work/app/pedestrian/private/breathing_model/`

The complete private folder is required, including the checkpoint, scaler, participant history, personal baseline and model metadata. These files are deliberately excluded from this public repository. Without them, the full CVAE solver cannot run; the public saved-journey demo still works independently.

Launch:

```powershell
local-source/.venv/Scripts/python.exe local-source/.work/app/pedestrian/launch.py
```

The browser opens automatically. Keep the Python process running. The server binds to localhost and blocks private files from browser downloads.

## Included behaviour

Arbitrary mapped endpoints; walking/running selected before departure; real departure time; shared person/traffic/environment time; smoothly repeated pollution and temperature with full-map estimates; arrival-time wave branching; sunlight and thermal comfort; personal health-score contributions; crossing waits for modelled lights and retained vehicle gaps; pink arrows, red plots and camera following.

The CVAE weights and recorded activity remain unchanged. Running-specific breathing is not calibrated. Read `SHARED_CLOCK.md` for current assumptions; environmental estimates, health scores and crossing checks are research scenarios, not clinical or real-world safety guarantees.

## For collaborators and Codex

Preserve newer roads, walking permissions, terrain, environmental providers, vehicle trajectories and native traffic controls. Adapt the modules instead of overwriting newer urban assets. Prefer native pedestrian signal timing where available; otherwise retain labelled modelled pedestrian lights and vehicle-gap checks. Keep candidate arrival times, waiting costs, exposure and CVAE history aligned. Never add participant histories, model weights, baseline source files, caches or a portable ZIP to this public repository.

Run relevant tests under `pedestrian/tests`. Some integration tests expect a running app on port 8811. The checked portable package remains available to authorised collaborators in the separate private repository; no new release is required to update this source folder.
