         # OKC Future Transit Planner

A runnable **Python + Streamlit + Folium** prototype of Central Oklahoma's proposed future transit network, with **MVC architecture**, an **Observer pattern**, transit-only routing with NetworkX, NumPy-accelerated distance calculations, a lightweight rounded dashboard, and estimated trip statistics.

> **INDEPENDENT STUDENT PROJECT — NOT AN OFFICIAL TRANSIT SERVICE.** This is a UCO student-built educational simulation. It is **not affiliated with, sponsored by, approved by, or endorsed by ONE Transit or any transit agency**. The project does not speak for ONE Transit. The network, stop locations, service patterns, travel times, fares, and scenario inputs are conceptual and are not real-world navigation guidance.

> **SCENARIOS, NOT VERIFIED OUTCOMES.** Figures about potential riders, car journeys, CO₂, maintenance costs, reading/study time, traffic, noise, and safety explore possibilities; they do **not** establish actual effects, guarantees, or official forecasts. Presenting a possibility does **not** mean the project accepts it as true or rejects it as false. Published national factors are references, not local forecasts. Crash prevention, net CO₂ reductions, decibel reductions, and congestion improvements are **not quantified or claimed**. Other effects and trade-offs may be outside this model.

The simulator is inspired by [ONE Transit's public planning information](https://www.onetransit.org/discover/), linked for attribution rather than to imply an endorsement. Please consult official sources for real service and planning decisions.

## Launch in VS Code (macOS)

If you previously built this project step-by-step, **back up the existing folder first**. Then extract this ZIP into its own folder; it includes everything.

```bash
cd okc-future-transit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit will show the local URL (usually `http://localhost:8501`). You need an internet connection for the tile map and optional web fonts.

Windows PowerShell:

```powershell
cd okc-future-transit
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Features

- Ten color-coded lines matching the categories in the provided ONE Transit future-system map (four primary regional proposals and six conceptual connector/extension layers).
- Two network modes: **all system-map layers**, or **four regional corridors only**.
- Fixed OpenStreetMap basemap; no API key or map-style selector.
- **Interactive map switch (off by default):** locked map shows corridors and selected points without allowing movement or clicks; use the start/end dropdowns instead.
- **Interactive map on:** all station circles appear. Drag or zoom without causing Streamlit reruns; only clicks on actual station circles select a trip (first click start, second click destination, third click starts a new trip). No free-space guessing.
- Controls are reorganized into collapsible sidebar settings, route details/export, and the map legend.
- **Random trip** always generates two different connected locations.
- **No cars, no walk shortcuts, no automatic road routing**: NetworkX can travel only between consecutive boarding points defined on the same transit line and switch lines only at an explicitly shared stop ID.
- Shortest approximate travel-time route, with leg-by-leg details and transfer points.
- Static route highlighting and selected start/end markers (no expensive pulse overlays). Rounded buttons and metric cards remain.
- Time, modeled fare, transfers, and savings where the example indicates them. Negative results are clearly presented as extra cost or extra time, not hidden.
- Export a trip itinerary as JSON.
- Accessible note: browser prefers-reduced-motion is honored in the UI stylesheet.

## Additional potential community benefits (scenario only)

The expanded **Potential community benefits** panel now includes:

- **Possible onboard reading/study time per rider**, based on modeled in-vehicle minutes and an editable share of time that might be usable. This is *not* extra time saved compared with driving, and may not be practical for all passengers or journeys.
- **Potential maintenance/repair/tire cost component** from displaced car miles. The default of **$0.1104 per car mile** is from [AAA's 2025 Your Driving Costs fact sheet](https://newsroom.aaa.com/wp-content/uploads/2025/09/UPDATE-AAA-Fact-Sheet-Your-Driving-Cost-9.2025-1.pdf). **Do not add this to the existing vehicle-cost comparison**, which already includes operating costs.
- **Potential replaced car journeys**, derived from hypothetical riders, their assumed car-replacement share and average vehicle occupancy. This is not a measured congestion reduction.
- Qualitative notes on traffic, noise, parking and road safety, without claiming a measurable reduction in decibels, crashes or traffic delays. [FHWA's traffic noise guidance](https://www.fhwa.dot.gov/Environment/noise/regulations_and_guidance/analysis_and_abatement_guidance/polguide01.cfm) explains why sound levels cannot be reduced by simply subtracting a per-car decibel value.

Controls for these assumptions remain in a **collapsed** expander below the community metrics. The app sidebar starts **collapsed**, and station dropdown labels use text-only service categories.

## Project structure / MVC + Observer

```text
okc-future-transit/
├── app.py                         # Streamlit entry point, input widgets
├── controllers/
│   └── route_controller.py       # Handles trip selection, random trips, event dispatch
├── models/
│   ├── station.py                # Boarding location (conceptual)
│   ├── transit_line.py           # Ordered stops and independent route geometry
│   ├── transit_network.py        # JSON loader + validation
│   ├── route_calculator.py       # NetworkX transit-only shortest path + transfers
│   └── statistics.py             # Modeled comparisons (doesn't route a car)
├── observers/
│   ├── subject.py                # TripState Subject; attach/detach/notify
│   ├── map_observer.py           # Reacts by updating selected map trip
│   └── statistics_observer.py    # Reacts by recomputing KPI values
├── views/
│   ├── map_view.py               # Folium layers, lazy stop rendering
│   └── statistics_view.py        # Styled KPI and leg HTML
├── data/
│   ├── stations.json             # Edit station names / coordinates / IDs
│   └── routes.json               # Edit line geometry, stops, speeds and colors
├── assets/
│   ├── styles.css                # Layout, rounded corners, hover transitions
├── tests/test_network.py
├── requirements.txt
└── .streamlit/config.toml
```

**Observer flow**:

`User changes trip → RouteController.plan_trip(...) → TripState.set_trip(...) → notify registered MapObserver + StatisticsObserver → View renders observer snapshots.`

Streamlit reruns the script after a user action, but **the Observer pattern is explicitly implemented in Python**: `TripState` has `attach()`, `detach()` and `set_trip()`, and it calls each observer's `on_trip_changed()`.

## How routing works

Each vertex represents `(station_id, line_id)` — boarding the same station on two different lines produces two vertices. Edges are defined for **adjacent stops on each line**, plus **transfers only at identical station IDs**. Transfer time and initial waiting time are included in shortest-path weights. There are no roads or walking edges. Styling coordinates do not create graph connections by proximity.

A line has both:

- `station_ids` — ordered *boardable* locations.
- `path_coordinates` — polyline points just for display; `stop_indices` point to each station's position along this shape.

To add a true interchange, make both lines reference the **same station ID**. Two coordinates that happen to be close are **not** connected automatically.

## Savings calculation (illustrative, adjustable)

The app does **not** provide a car journey or any vehicle route. It compares the computed transit time/fare to a synthetic benchmark:

```
benchmark distance  = straight-line distance × 1.28 (assumed road detour)
benchmark time      = benchmark distance / 31 mph × 60 + 3 minutes
benchmark cost      = benchmark distance × $0.67/mile + $2 parking
transit fare        = $2.50 flat (example)
money saved         = benchmark cost − transit fare
time saved          = benchmark time − transit time
```

Negative time saved **means transit takes longer**, and negative money saved **means transit costs more** under the assumptions. Transit travel times are calculated using approximate polyline miles, illustrative corridor speeds, 0.7 minutes per intermediate leg, initial wait and per-transfer penalties. These are **not** service predictions.

## Geography / responsible use

ONE Transit's published plan identifies four high-capacity regional corridors:

1. Commuter rail, Edmond ↔ downtown Oklahoma City ↔ Norman (the existing BNSF corridor).
2. West Regional Bus Rapid Transit, west Oklahoma City ↔ downtown (10th / MacArthur / Reno / Council / 15th corridor).
3. East Regional Bus Rapid Transit, downtown ↔ Tinker AFB (Reno / Eastern / SE 29th corridor).
4. Airport Light Rail, downtown ↔ airport (Reno / Meridian corridor).

The image also shows MAPS 4 BRT, EMBARK RAPID, Citylink Edmond, EMBARK OKC, EMBARK Norman, and an Airport Light Rail FAA extension. This prototype **adds those as deliberately simplified illustrative connections**, not verified individual bus routes or final stops.

The map in the user's image says **N.T.S. (not to scale)**, so our station pins and simplified bends are not georeferenced or officially surveyed. Airport, campus and State Capitol pins are landmark proxies. In particular, a UCO campus pin is **not** asserted to be a commuter rail station. Core West BRT stops are not finalized in ONE Transit's published description.

**Sources:**
- [ONE Transit — Discover the Plan](https://www.onetransit.org/discover/)
- [ONE Transit — Commuter Rail](https://www.onetransit.org/commuter-rail/)
- [ONE Transit — West BRT](https://www.onetransit.org/brt-west/)
- [ONE Transit — East BRT](https://www.onetransit.org/brt-east/)
- [ONE Transit — Airport Light Rail](https://www.onetransit.org/airport-light-rail/)

This is an independent demo, **not** affiliated with ONE Transit.

## Tests

```bash
python -m pip install pytest
python -m pytest -q
```

The tests cover JSON geometry integrity, valid/invalid routes, transfer restrictions, reverse journeys, randomly chosen connected trips, real Observer notifications and savings assumptions.

## Customize it later

1. Replace approximate pin coordinates in `data/stations.json` with verified proposed boarding locations, **not** landmark centers.
2. Update `data/routes.json` with surveyed shape points and matching `stop_indices` (one per `station_ids` entry, increasing from the start). **Every selected shape point must exactly equal its referenced station coordinates**; the Model validates this on load.
3. Add authentic timetables / stop-to-stop travel time weights instead of estimated speeds.
4. Replace the hypothetical comparison model with validated fare/traffic data if available.
5. Add a data-feed Subject and observers for live service events when data actually exists.

`tests/test_network.py` should continue to pass after edits.

## Performance design (November 2026 update)

- **Click sequence:** first map click chooses a start, second chooses a destination, and the next starts a new trip. Selecting a start in the dropdown clears the old destination.
- **Lazy stop markers:** at startup the Folium map draws transit corridors only. Nonselected station pins are **not rendered** until you turn on “Reveal all station pins”. The station coordinate catalog still loads into Python (32 records) because invisible points cannot otherwise be discovered from map clicks. Clicking near a point performs a fast nearest-stop lookup; a click must be within about 0.9 miles of a known conceptual point.
- **Lazy routing:** NetworkX graph creation waits until a complete trip is requested or you choose Random Trip; datasets are cached with Streamlit.
- **NumPy:** lazily imported by the distance calculations and nearest-stop lookup, reducing Python loops. NetworkX still solves the tiny sparse transit graph, which is appropriate for this size.
- **Tiles:** OpenStreetMap only loads visible map tiles; the map is restricted to the OKC network region. Tile servers still require internet connectivity but not an API key. OpenStreetMap public tiles have usage limits; a dedicated tile provider is recommended if deployed to many public users.
- **Motion:** map overlays and hover animations are static to minimize browser rendering work.
- **Comparison:** savings are estimates derived from editable assumptions; positive numbers are emphasized without concealing negative ones.

You may run tests with `python -m pytest -q` after installing `pytest`.

## Map refresh fix (November 2026)

The old version listened to `center`, `zoom`, `last_clicked`, and circle clicks; ordinary dragging could therefore trigger full Streamlit reruns. This version restricts `st_folium(returned_objects=...)` to `last_object_clicked` and `last_object_clicked_count`. It only calls `st.rerun()` following a new station circle click. In locked mode, the map is rendered in a non-communicating iframe with Leaflet dragging/zoom/clicking disabled.

These changes prevent reruns caused by pan/zoom, but selecting a station or changing a Streamlit widget still reruns the Python script as expected. We could not run a full interactive browser test in the build environment, so please verify the map behavior in your local Streamlit app.


## Potential community benefits (illustrative)

The collapsed **Potential community benefits** section estimates a scenario for one departure: possible riders (limited to an example vehicle capacity), car travel potentially replaced, and gross car tailpipe CO₂ potentially avoided. These calculations use editable assumptions, **not** observed ridership or validated fleet capacities. They do not subtract emissions from transit operations and cannot establish net CO₂ savings. Crash prevention is intentionally described only as a possibility; the application never claims actual accidents avoided. The primary KPI cards display positive savings only when present. The methodological notes disclose underlying numerical comparisons, including less favorable cases. Default initial wait and transfer assumptions are 2 and 3 minutes respectively, not official schedules.


## Layout and station selection update (November 2026)

- Potential Community Benefits opens by default in a right-hand column alongside the map, rather than below it. On narrow screens Streamlit may stack columns responsively.
- Starting point and Destination selectors are visually organized into Transfer hubs, Rail, Rapid bus, and Local bus. Each shared station appears once.
- Community impact figures remain illustrative what-if scenario estimates, not measured outcomes.


## Source-backed community scenario (2026 update)

The right-side community benefits panel opens by default. Its editable sliders are nested directly beneath the benefits summary in **Adjust community scenario**. Journey details remain collapsed until opened. Icons/emoji have been removed from the UI labels.

**Grounding:** FTA 2024 EMBARK agency profile reports 3,244,979 annual unlinked boardings (https://www.transit.dot.gov/sites/fta.dot.gov/files/transit_agency_profile_doc/2024/60017.pdf), which are not a forecast for this conceptual route. The US Department of Energy reports 1.5 persons per household vehicle trip based on 2022 NHTS (https://www.energy.gov/cmei/vehicles/articles/fotw-1333-march-11-2024-2022-average-number-occupants-trip-household). EPA estimates ~400 g CO2/mile for a typical passenger vehicle (https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle). The 20-passenger starting scenario, replacement share, and bus/rail capacity are **unverified user-editable assumptions**, not sourced ridership or fleet capacity. No crash reduction number is asserted.


## Public sharing and attribution

The Streamlit app displays a visible independence statement at the top, detailed limitations in an expandable section, and a reminder alongside the community estimates. A public link to ONE Transit's planning materials replaces the previously bundled third-party reference image. This does not imply ONE Transit reviewed or supports the simulation.

The app is an exploratory software engineering exercise. It neither endorses nor rejects hypotheses about community impacts; further localized evidence would be needed before drawing policy or safety conclusions.
