# Local connected walking, traffic and environment — 16 November 2026

Run `Start-Canopy-Pedestrian.cmd`, then open the local viewer on port 8811.
This change is local only; the GitHub Pages saved-journey edition is unchanged.

Walking, the Traffic view, and the Pollution view share play/pause, speed and
seeking. Scenario time is `start time + elapsed walking time`, including waiting.
Scenario zero is aligned with the first recorded SUMO frame, labelled 08:50:00.
This is an explicit scenario alignment, not evidence that the separate simulations
were recorded as one real-world event. Traffic retains its exact 1-second frames;
at fractional times the latest available frame is displayed without inventing motion.

The full route-model coverage is restored: 0–46,800 seconds (13 hours).
Later starts reduce the remaining breathing-model coverage, as before. The short
environmental and traffic recordings impose no additional journey limit.
Pollution and temperature repeat with `field_time = journey_time % 600`.
Traffic repeats its 600 one-second frames on the same 600-second cycle.
During seconds 540–600, pollution and temperature blend back to their initial
fields with smoothstep weight u²(3−2u), u=(phase−540)/60. This removes the
value discontinuity at each restart. The same blend is applied before PM conversion
in the planner, breathing inputs, health display and pollution map. It is a
synthetic replay transition; original field files and traffic frames are unchanged.
The display identifies the replay cycle and original traffic timestamp. This is
an explicitly repeated scenario, not a forecast of conditions over 13 hours.
Journey elapsed time, accumulated exposure, pedestrian signal schedules and the
CVAE physiological history continue across each cycle without resetting.

The planner, breathing-model inputs, route profiles, walking street colours and
current health score use the same saved Canopy fields and ENU coordinates.
Sampling uses the containing grid cell and linear interpolation between stored
times. The pollution grid is 8 m (6 m sampling height); temperature is 32 m
(8 m sampling height). These are near-ground model proxies, not wearable measurements.
The published pollution asset uses its existing 8-bit quantization; temperatures
retain float16 values. Source bytes, masks, road geometry and traffic trajectories
are preserved. Masked/out-of-domain samples remain unavailable in the health display.
The CVAE uses training-mean missing-field inputs, with an explicit routing penalty.

Canopy pollution is a road-source tracer in arbitrary units, not calibrated PM2.5.
For the existing PM2.5-input CVAE and illustrative score, the scenario conversion is:

`PM = 6 + 34 * clip(log1p(tracer / 0.001) / log1p(33.81 / 0.001), 0, 1)`

This estimate is labelled in the interface; it is not a measurement or validated
health prediction. The Pollution view displays the original tracer units.
There is no longer a separate sinusoidal walking pollution field in the active app.
Moving cars do not generate the saved tracer; time alignment is not a new emissions
simulation. Pedestrian signals still use modelled schedules and do not control saved cars.
Wind, sunlight, birds, UAVs and flooding retain their own unrelated scenario controls.

Breathing predictions keep the original recurrent CVAE's five-minute update phase
and recorded activity/humidity template. The health score samples the current
environment at the walker, including while waiting; it has no elapsed-time penalty.

Original changed files were backed up and hash-checked under
`../handoffs/local-clock-backup-20261116/` before editing. The original full release
also remains intact. Run `pedestrian/verify_preservation.py` to verify source assets.

Validation includes native field/time/coordinate and mask tests, cycle boundaries,
real local API routes at start times 0, 120, 600, 1200 and 45000 seconds,
a journey exceeding ten minutes, breathing-coverage rejection, retained breathing and
wave-method checks, JavaScript field/health/follow tests, and browser playback,
pause, cross-view seeking and traffic-frame agreement. The preceding bounded-clock
implementation is preserved in `../handoffs/local-replay-backup-20261116/`.

## Candidate-specific wave branching
Each retained history recomputes junction impedance from pollution and temperature
at its junction position and absolute arrival time (start + elapsed), plus its
current CVAE burden. It uses the same smooth environmental replay and missing-data
penalty as exposure integration. Source injection and the existing transmission
formula are preserved. Selected-path traces record branching density and impedance.
The bounded candidate shortlist still uses a departure guide; this is not a claim
of exhaustive time-dependent search or a globally optimal route.

## Experimental health score and reference audit
H=100 exp[-ln(100/90)(0.35(C/15)^2 + 0.15(max(18-T,T-26,0)/8)^2
+ 0.50(1.5 max(L-R,R-U,0)/s)^2)]. Constants are design choices, not clinical
thresholds. PM concentration remains a tracer-derived scenario. Contributions
allocate 100-H in proportion to each weighted squared burden; they are not
independent causal effects. Missing required inputs yield no score.

The retained personal_baseline.json was audited against personal_baseline_score.py:
63 complete pre-cutoff observations; all matched timestamps precede cutoff.
48 half-hour bins: 34 activity/time matches, 8 activity-only, 6 pooled fallbacks.
Minimum support is 8. Scale is max(local SD, global SD), at least 1.2118 breaths/min
in this artifact (defensive score scale floor 0.1). q10/q90 are descriptive, not
clinical. Activity is a retrospective recorded template, not verified walking.
Reference summaries follow history_offset + departure + elapsed, without resetting
at environmental replay boundaries. Raw observations and timestamps stay private.
The display uses the CVAE mean, not its particle-wise planning burden. The new
score changes the display only; planner objective coefficients remain unchanged.

Temperature coverage update: missing cells are now extended from nearest valid cells by Manhattan grid distance, with a shared donor map for Python and JavaScript. Original files remain unchanged. All frames are finite over the full domain; smooth temporal replay is preserved. Earlier missing-temperature descriptions are superseded.

Pollution coverage update: all missing tracer cells now use nearest valid donors by grid distance, shared between backend and browser. Original valid cells and source files remain unchanged; gap values are illustrative estimates. Both environmental fields have finite values over every grid cell in every frame. Health still requires a valid breathing prediction/reference and an in-domain position.

Breathing display sensitivity is now 1.5 times the standardised outside-band deviation (2.25 times its squared burden). Reference bands, predictions and route optimisation remain unchanged. This is display tuning, not clinical calibration.

Departure control now accepts HH:MM[:SS], anchored to traffic recording 08:50 (scenario zero). UI clock times map to unchanged model seconds; final journey coverage ends 21:50. This is a clock-labelled replay, not current-date weather or traffic. Breathing retains its independent historical template.


## Solar coupling (16 November 2026)
The local full app uses existing 8 m quantized clear-sky irradiance arrays:
21 June 2026, 99 ten-minute frames, 04:50-21:10 local scenario time;
21 December 2026, 47 ten-minute frames, 08:10-15:50.
Point samples use the containing cell and linear temporal interpolation of decoded
W/m2. Clock seconds = 31800 + departure_s + elapsed_s. Solar does not repeat with
the 600-second traffic/pollution/air-temperature scenario. Irradiance is zero
outside the selected day's daylight span (both endpoint frames are zero).
The selected day is explicit: no claim is made that this is current-date weather.
The main sunlight selector and walking panel selector are synchronized, and day
changes invalidate the calculated route. Irradiance display shares the journey
clock; the original binary shadow display uses the nearest native solar frame.

Thermal proxy: T_proxy = T_air + k * clip(I / 800, 0, 1.5), with default k=6 C
in pedestrian/scenario.json (solar_warming_c_per_800). This is a deliberately
simple configurable scenario heuristic, not UTCI, WBGT, a calibrated feels-like
temperature, a UV dose or a clinical health estimate. The selected solar day is
combined with the existing repeated thermal scenario, not a weather-consistent
seasonal forecast. Solar can relieve the provisional cold penalty or increase
the hot penalty. It can consequently leave a score unchanged within the comfort
band. Thermal score uses T_proxy in the existing 15% component; pollution and
breathing weights remain 35% and 50%, and score remains in (0,100].
The planner substitutes the same proxy in thermal traversal/wait cost and
branching density at each candidate's absolute arrival time, including the
departure guide. Planner and display retain their original different scaling.
CVAE still receives unmodified local air temperature and pollution with its
recorded remaining inputs. Model weights, reference bands, and update cadence
are unchanged. Exported route samples include sunlight and thermal_proxy.
The coefficients are design choices; irradiance alone cannot establish human
thermal stress. OSHA's heat guidance identifies radiant heat, humidity, air
movement and temperature as separate inputs:
https://www.osha.gov/heat-exposure/hazards

Tests cover local-day interpolation, evening zero, day/position dependence,
branch/traversal response, unchanged CVAE predictions with fixed air inputs,
and browser/backend sampled-field and live-score agreement.


## Recorded-traffic crossing gaps (16 November 2026)
The original roads, traffic binary, vehicle positions/headings and replay remain
unchanged. Each mapped pedestrian crossing now combines its modelled WalkGate
with a RecordedTrafficGaps admission check. No car is slowed, rerouted or added.

For each 1 s saved interval, the crossing polyline is checked against each retained
vehicle's swept bounding disc between consecutive positions. Generic body sizes
match the viewer: car 4.5 x 1.85 m; bus 11.5 x 2.5 m. Disc radii are body half-
diagonals, enlarged by 1.4 m (walker radius 0.4 m plus 1 m separation). Stationary
vehicles use point footprints, so stopped vehicles remain obstacles. Occupied
intervals expand by 1 s in both directions and repeat with the 600 s replay.
The final recorded position is held until reset; no fictional sweep connects
last to first frame. The loop boundary is still checked on both sides.

Admission requires a valid pedestrian-light window AND the entire crossing
corridor free throughout travel plus 2 s clearance. This is conservative: it
rejects vehicles anywhere along the crossing, even before the walker would
reach their location. XY checks may also over-block grade-separated traffic.
Only retained simulated vehicles are covered, with full knowledge of saved
future trajectories; omitted traffic is not reconstructed. These margins and
generic bodies are scenario choices, not validated road-safety thresholds.

The same gate is used in timed candidate generation, candidate feasibility,
wave entrance release and final route reconstruction. A packet remains frozen
in its zero-speed entrance strip until the combined gate admits it. Empty hold
steps are skipped exactly, while cost.wait advances exposure and CVAE state
for the full hold. Waiting is included before downstream propagation, not
appended after route selection. A crossing without a valid gap before the
journey deadline is rejected; there is no unsafe fallback.

The selected route exports periodic blocked intervals for its crossing heads.
Heads show WAIT if either the signal or vehicle-gap/clearance test is closed.
The status card identifies traffic/light waits; the plot accumulates both.
traffic_wait_s reports extra delay relative to light-only admission, including
any additional signal cycle missed because of cars. It is not a separate
physical exposure duration; all waiting is already included once in wait_s.

Cached occupancy is private under pedestrian/cache. Its key includes traffic
binary, metadata, crossing geometry, margin constants and algorithm version.
Source arrays are untouched. CVAE checkpoint and cadence remain unchanged.
Tests cover stopped buses, swept motion, clearance, deadlines, reverse travel,
replay seams, exact wave release, wait exposure and a traffic-avoiding detour.
A real crossing starting at t=590 s waits 88 s (58 s additional traffic delay)
and triggers its next CVAE update at elapsed t=10 s during the hold.


## Walking/running selected before departure (16 November 2026)
API travel_mode is walk (default, 4/3 m/s = 4.8 km/h) or run (2.5 m/s =
9 km/h). These fixed presets are scenario choices, not measured personal speeds.
Unsupported modes are rejected. The public API derives physical speed from the
mode rather than trusting a caller-supplied arbitrary speed.

Each plan uses request-local Edge copies carrying the selected speed. Candidate
travel estimates, wave propagation, CVAE/environment transition positions and
final timelines all use that same speed, including mapped road crossings.
Traffic occupancy and source roads are unchanged; gap admission and exported
pedestrian-light checks use the mode-specific crossing duration plus the same
2 s clearance. Traffic waiting may therefore change nonlinearly with speed.
Waiting remains stationary and still advances pollution/temperature/solar
exposure, breathing history and physical time. No mode changes alter replay
speed: the playback-rate control is a separate simulation-time multiplier.

The mode selector is available before departure. Any change invalidates the
previous route. It locks after the journey advances, including while paused
or rewound; New journey clears the route and unlocks it. Changing endpoints or
other planning inputs also starts a fresh plan. No mid-journey mode transition
or physiological-history transfer is implemented.

The existing CVAE takes act_level, step_count and walking, but has no running
category or calibrated speed-to-activity mapping. Its weights, recorded activity
inputs, personal reference bands and five-minute update interval are preserved.
Running changes exposure timing, not the activity-template covariates. Running
breathing/health outputs are explicitly labelled as not calibrated for running;
no artificial breathing-rate multiplier is applied. Future running physiology
requires a validated mapping/data rather than inferring it from animation speed.
