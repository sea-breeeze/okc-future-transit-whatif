"""OKC Future Transit Planner — MVC + Observer Pattern demonstration.

Run with: python -m streamlit run app.py
All corridor and stop positions are explicitly approximate; see README.md.
"""
from pathlib import Path
import json
import streamlit as st

from controllers.route_controller import RouteController
from models.transit_network import TransitNetwork
from models.statistics import ComparisonSettings
from models.community_benefits import BenefitAssumptions, estimate_community_benefits
from models.route_calculator import nearest_station_id
from views.map_view import build_map
from views.statistics_view import kpi_html, leg_html

BASE = Path(__file__).resolve().parent
st.set_page_config(page_title="OKC | Future Transit Planner", page_icon="",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown(f"<style>{(BASE / 'assets' / 'styles.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_network():
    """JSON files and immutable network definitions load once per app process."""
    return TransitNetwork()


def choose_random(controller: RouteController) -> None:
    start, end = controller.generate_random_trip()
    st.session_state["origin_id"] = start
    st.session_state["destination_id"] = end
    st.session_state["map_next"] = "start"
    st.session_state["map_notice"] = "Random connected trip selected. Click another point to start a new trip."


def swap_trip() -> None:
    st.session_state["origin_id"], st.session_state["destination_id"] = (
        st.session_state["destination_id"], st.session_state["origin_id"]
    )
    st.session_state["map_next"] = "start"


def change_origin() -> None:
    """Manual start selection begins a new trip."""
    st.session_state["destination_id"] = None
    st.session_state["map_next"] = "end" if st.session_state["origin_id"] else "start"


def change_destination() -> None:
    st.session_state["map_next"] = "start" if st.session_state["destination_id"] else "end"


def apply_pending_map_selection() -> None:
    station_id = st.session_state.pop("pending_map_selection", None)
    if station_id is None:
        return
    # The third click always starts a NEW journey instead of changing an
    # existing destination. No radio button or manual reset required.
    if st.session_state.get("map_next", "start") == "start":
        st.session_state["origin_id"] = station_id
        st.session_state["destination_id"] = None
        st.session_state["map_next"] = "end"
    elif station_id != st.session_state.get("origin_id"):
        st.session_state["destination_id"] = station_id
        st.session_state["map_next"] = "start"
    else:
        st.session_state["map_notice"] = "Choose a different point for your destination."


# --------------------------------------------------------------------
# SIDEBAR: inputs and simulation assumptions, not routing implementation.
# --------------------------------------------------------------------
with st.sidebar:
    st.markdown('''<div class="sidebar-logo"><div class="sidebar-emblem">OKC</div>
    <div class="sidebar-brand">OKC TRANSIT<br><small>Future network lab</small></div></div>''',
    unsafe_allow_html=True)
    with st.expander("Network coverage", expanded=False):
        scope = st.radio(
            "Service coverage",
            ["All services in the plan", "Four regional corridors"],
            key="service_scope",
            help="The other services are conceptual connectors based on the supplied system-map legend."
        )
    include_local = scope == "All services in the plan"
    with st.expander("Map and trip options", expanded=False):
        show_comparison = st.toggle("Show estimated savings", value=True)
        zoom_to_trip = st.toggle("Focus new trips on map", value=False)
    with st.expander("Scenario settings · travel time", expanded=False):
        st.caption("Assumptions are not verified fares or timetables.")
        initial_wait = st.slider("Initial wait (minutes)", 0, 20, 2, 1)
        transfer_minutes = st.slider("Time per transfer (minutes)", 0, 20, 3, 1)
    with st.expander("Scenario settings · fare and comparison", expanded=False):
        fare = st.number_input("Illustrative transit fare ($)", 0.0, 25.0, 2.50, 0.25)
        cost_per_mile = st.number_input("Vehicle cost per mile ($)", 0.0, 3.0, 0.67, 0.05)
        parking = st.number_input("Parking/other cost ($)", 0.0, 40.0, 2.0, 0.5)
        comparison_speed = st.slider("Comparison average speed (mph)", 10, 70, 31, 1)
    st.divider()
    with st.expander("Planning inspiration and project status", expanded=False):
        st.markdown(
            "Independent UCO student project. Not affiliated with, sponsored by, "
            "approved by, or endorsed by ONE Transit or any public agency. "
            "[View ONE Transit's official planning materials]"
            "(https://www.onetransit.org/discover/)."
        )
    st.markdown('<div class="sidebar-note">A planning concept, not live navigation. No driving route is created or displayed.</div>',
                unsafe_allow_html=True)

# --------------------------------------------------------------------
# MODEL and CONTROLLER
# --------------------------------------------------------------------
network = get_network()
controller = RouteController(network, include_local=include_local,
                             initial_wait=initial_wait, transfer_minutes=transfer_minutes)
stations = controller.get_stations()
lines = controller.get_lines()
# Organize destinations by service type, with transfer hubs shown first.
# Streamlit selectboxes do not have native optgroup headers, so each item
# has a clear category prefix. A shared station appears only once.
station_services = {sid: set() for sid in stations}
for line in lines.values():
    for sid in line.station_ids:
        if sid in station_services:
            station_services[sid].add(line.mode)


def station_category(sid):
    services = station_services[sid]
    if len(services) > 1:
        return (0, "Transfer hub")
    if "Commuter rail" in services or "Light rail" in services:
        return (1, "Rail")
    if "Bus rapid transit" in services:
        return (2, "Rapid bus")
    return (3, "Local bus")


station_ids = sorted(stations, key=lambda sid: (
    station_category(sid)[0], stations[sid].name.lower()))


def station_label(sid):
    if sid is None:
        return "Choose a location…"
    return f"{station_category(sid)[1]}  ·  {stations[sid].name}"

# Apply click events before constructing Streamlit widgets.
apply_pending_map_selection()
if st.session_state.get("origin_id") not in stations:
    st.session_state["origin_id"] = None
if st.session_state.get("destination_id") not in stations:
    st.session_state["destination_id"] = None
if "map_next" not in st.session_state:
    st.session_state["map_next"] = "start"
settings = ComparisonSettings(fare_usd=fare, vehicle_cost_per_mile=cost_per_mile,
                              parking_usd=parking, road_speed_mph=comparison_speed)

# --------------------------------------------------------------------
# HEADER
# --------------------------------------------------------------------
st.markdown('''
<section class="hero">
  <div class="hero-kicker">ONE REGION · MORE POSSIBILITIES</div>
  <div class="hero-title">Your city's next connection.</div>
  <div class="hero-desc">Explore an interactive simulation of Central Oklahoma's future transit network.
  Find routes, change lines, and see how a connected region could work.</div>
  <div class="hero-tags"><span class="hero-tag">✧ FUTURE SYSTEM CONCEPT</span>
  <span class="hero-tag">↗ TRANSIT-ONLY ROUTING</span><span class="hero-tag">◇ MVC + OBSERVER</span></div>
</section>''', unsafe_allow_html=True)

# Keep this visible on the public site; it is not an official transit tool.
st.caption(
    "INDEPENDENT UCO STUDENT PROJECT · Not affiliated with, sponsored by, "
    "approved by, or endorsed by ONE Transit or any transit agency. "
    "Conceptual map only; not for actual travel planning."
)
with st.expander("Project independence and important limitations", expanded=False):
    st.markdown("""
    **Independent educational demonstration.** This software is a student-created
    exploration of possible transit connections. ONE Transit and other transit
    agencies have not reviewed, approved, sponsored, or endorsed the project.
    Names and links identify planning inspiration, not a partnership.

    **Not official travel guidance.** Locations, route alignments, transfers,
    service speeds, fares, waiting times, and vehicle capacities may be
    simplified or invented for the simulation. Do not rely on this app for
    travel, service availability, or public policy decisions.

    **No position taken on potential impacts.** Ridership, displaced car trips,
    CO₂, maintenance costs, study time, traffic, noise, parking, and safety are
    possibilities explored through user-adjustable assumptions. The project
    **neither verifies nor dismisses** these potential effects. Displaying a
    scenario is not evidence that it will occur, or a claim that an agency
    agrees with it. Published national reference factors are not local
    forecasts. Other impacts and trade-offs may exist outside this model.

    **Safety and emissions limits.** No number of crashes prevented, decibels
    reduced, or net emissions saved is established by this model. Gross
    avoided car-tailpipe CO₂ does not include transit emissions.

    **Sources:** [ONE Transit planning information](https://www.onetransit.org/discover/).
    Published factors and their limitations appear under **Sources and evidence**
    in the Community Benefits panel.
    """)

# --------------------------------------------------------------------
# LEFT: INTERACTIVE TRIP INPUTS
# --------------------------------------------------------------------
left, right, benefits_col = st.columns([0.90, 1.75, 1.08], gap="medium")
with left:
    st.markdown('''<div class="trip-header"><strong>Plan your journey</strong>
        <span class="dot-label">● Interactive</span></div>''', unsafe_allow_html=True)
    st.button("Surprise me with a valid trip", on_click=choose_random,
              kwargs={"controller": controller}, use_container_width=True, type="primary")
    st.selectbox("Starting point", [None] + station_ids,
                 format_func=station_label,
                 key="origin_id", on_change=change_origin)
    st.selectbox("Destination", [None] + station_ids,
                 format_func=station_label,
                 key="destination_id", on_change=change_destination)
    if st.session_state["origin_id"] and st.session_state["destination_id"]:
        st.button("Swap start and destination", on_click=swap_trip,
                  use_container_width=True, type="secondary")
    step_text = ("Click near a station to choose your START."
                 if st.session_state["map_next"] == "start"
                 else "Now click near another station to choose your DESTINATION.")
    st.info(step_text)
    if st.session_state.pop("map_notice", None):
        st.caption("Selections update immediately. Click again to plan another trip.")
    st.markdown('<div class="trip-guide">Only the future-system lines and shared transfer stations '
                'are allowed. Routes never jump between nearby unconnected places.</div>',
                unsafe_allow_html=True)

    start_id = st.session_state["origin_id"]
    end_id = st.session_state["destination_id"]
    trip = None
    if start_id and end_id:
        if start_id == end_id:
            st.warning("Please choose two different locations.")
        else:
            trip = controller.plan_trip(start_id, end_id, settings)
            if trip is None:
                st.warning("No transit-only connection exists for this pair of points.")
    with st.expander("Journey details and export", expanded=False):
        if trip:
            st.markdown(f'<div class="section-sub">{len(trip.legs)} service leg(s) · '
                        f'{trip.transfers_count} transfer(s) · approximately {trip.miles:.1f} transit miles</div>',
                        unsafe_allow_html=True)
            st.markdown(leg_html(trip, stations, lines), unsafe_allow_html=True)
            st.caption("Trip total also includes starting wait and any transfer time.")
            summary = {
                "from": stations[start_id].name, "to": stations[end_id].name,
                "estimated_transit_minutes": round(trip.minutes, 1),
                "transfers": list(stations[x].name for x in trip.transfers),
                "route": [{"line": lines[leg.line_id].name,
                           "board": stations[leg.from_id].name,
                           "exit": stations[leg.to_id].name,
                           "estimated_minutes": round(leg.minutes, 1)} for leg in trip.legs],
                "warning": (
                    "Independent UCO student project; not affiliated with or endorsed by ONE Transit. "
                    "All routes, stops, travel times, fares and community outcomes are illustrative "
                    "and unverified; scenarios neither confirm nor dismiss possible impacts. "
                    "Not for real-world travel planning."
                )
            }
            st.download_button("Export trip details (JSON)",
                               data=json.dumps(summary, indent=2),
                               file_name="okc_concept_transit_trip.json", mime="application/json",
                               use_container_width=True)
        else:
            st.info("Select two connected places to show the service-by-service journey.")

# --------------------------------------------------------------------
# RIGHT: OBSERVERS provide presentation state to the Views
# --------------------------------------------------------------------
with right:
    st.markdown(f'''<div class="map-header"><strong>Future network map</strong>
      <span class="map-pill">{len(lines)} LINES · {len(stations)} POINTS</span></div>''',
      unsafe_allow_html=True)
    # Locked mode never sends map events to Streamlit. Interactive mode
    # listens to STATION CIRCLES ONLY (not pan/zoom/background clicks).
    map_interactive = st.toggle(
        "Enable interactive map", value=False, key="map_interactive",
        help="Off: stable map with no pan, zoom, or station clicking. On: move the map and choose start/end by clicking station circles.",
    )
    st.caption(
        "Map locked · use Starting point / Destination above."
        if not map_interactive else
        "Map active · drag to move; click a circle for START, then another for DESTINATION. Next circle begins a new trip."
    )
    map_widget = build_map(
        stations, lines, controller.map_observer.selected_itinerary,
        origin_id=start_id, destination_id=end_id,
        reveal_stations=map_interactive, zoom_to_trip=zoom_to_trip,
        interactive=map_interactive,
    )
    if map_interactive:
        # Only marker clicks are reported. Pan/zoom do not become application
        # events, so they cannot trigger the old constant refresh cycle.
        from streamlit_folium import st_folium
        map_event = st_folium(
            map_widget, height=540, use_container_width=True,
            key=f"okc_station_map_{'all' if include_local else 'regional'}",
            returned_objects=["last_object_clicked", "last_object_clicked_count"],
        )
        if map_event:
            click = map_event.get("last_object_clicked")
            count = map_event.get("last_object_clicked_count")
            # Prefer a monotonically increasing count so clicking the same pin
            # again after another interaction still works.
            if isinstance(click, dict) and "lat" in click and "lng" in click:
                token = (round(float(click["lat"]), 7),
                         round(float(click["lng"]), 7), count)
                seen = st.session_state.get("last_station_click")
                if token != seen:
                    st.session_state["last_station_click"] = token
                    station_id = nearest_station_id(
                        [click["lat"], click["lng"]], stations
                    )
                    if station_id is not None:
                        st.session_state["pending_map_selection"] = station_id
                        st.rerun()  # A marker was deliberately clicked.
    else:
        # A plain iframe has no Streamlit event bridge. Disabling Leaflet
        # interactions makes this a truly stationary display.
        import streamlit.components.v1 as components
        components.html(map_widget.get_root().render(), height=540, scrolling=False)

    with st.expander("Map legend", expanded=False):
        st.markdown('<div class="line-key">'
                    '<span><i style="background:#18af92"></i>Start</span>'
                    '<span><i style="background:#f07166"></i>Destination</span>'
                    '<span><i style="background:#f0ad38"></i>Transfer</span>'
                    '<span><i style="background:#355ed0"></i>Selected transit route</span>'
                    '</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-head">Trip at a glance</div>', unsafe_allow_html=True)
    st.markdown(kpi_html(controller.statistics_observer.stats, show_comparison),
                unsafe_allow_html=True)
    st.markdown('<div class="footnote">All routes are simplified conceptual alignments based on '
                'the user-provided future-system map and the ONE Transit corridor descriptions. '
                'Pins are not verified stops; durations, frequencies, fares, and savings are simulations.</div>',
                unsafe_allow_html=True)

with benefits_col:
    st.markdown('<div class="section-head">Community outlook</div>', unsafe_allow_html=True)
    # All impact values are conditional what-if scenarios, not forecasts.
    # Keep the primary dashboard compact; secondary assumptions and notes
    # remain collapsed and below the metrics.
    with st.expander("Potential community benefits · what-if scenario", expanded=True):
        # Read prior widget state before rendering controls below the metrics.
        # Widget keys ensure changes are applied on the next Streamlit rerun.
        passenger_scenario = st.session_state.get("community_riders", 20)
        replacement_share = st.session_state.get("community_car_share", 60)
        average_occupancy = st.session_state.get("community_occupancy", 1.5)
        co2_factor = st.session_state.get("community_co2_factor", 0.40)
        bus_capacity = st.session_state.get("community_bus_capacity", 40)
        rail_capacity = st.session_state.get("community_rail_capacity", 150)
        usable_share = st.session_state.get("community_usable_share", 60)
        maintenance_rate = st.session_state.get("community_maintenance_rate", 0.1104)

        if trip and controller.statistics_observer.stats:
            stats = controller.statistics_observer.stats
            assumptions = BenefitAssumptions(
                potential_passengers=passenger_scenario,
                car_trip_replacement_share=replacement_share / 100,
                average_car_occupancy=average_occupancy,
                tailpipe_kg_co2_per_car_mile=co2_factor,
                illustrative_bus_capacity=bus_capacity,
                illustrative_rail_capacity=rail_capacity,
                usable_onboard_time_share=usable_share / 100,
                maintenance_usd_per_car_mile=maintenance_rate,
            )
            benefits = estimate_community_benefits(trip, stats, lines, assumptions)
            st.caption(
                "**Exploratory what-if estimates only.** These are not observed outcomes, "
                "verified predictions, or ONE Transit positions. The model neither "
                "confirms nor dismisses these possible benefits. Results depend on "
                "the user-adjustable assumptions below."
            )
            st.metric("Potential riders", f"{benefits.potential_passengers:,}")
            st.metric("Car miles potentially replaced", f"{benefits.potential_displaced_car_miles:,.1f} mi")
            st.metric("Gross car tailpipe CO₂ potentially avoided", f"{benefits.potential_gross_tailpipe_co2_kg:,.1f} kg")
            st.metric("Potential car journeys replaced", f"{benefits.potential_displaced_car_trips:,.1f}")
            st.metric("Possible reading / study time per rider", f"{benefits.potential_usable_onboard_minutes_per_rider:,.0f} min")
            st.metric("Maintenance cost component potentially avoided", f"${benefits.potential_maintenance_usd_avoided:,.2f}")
            st.caption(
                "Study time is a share of estimated time **on board**, not extra time saved versus driving. "
                "It assumes riders can use that time productively; waiting and transfers are excluded. "
                "The maintenance figure is a component of vehicle operating costs, **not an extra amount "
                "to add to the existing driving-cost comparison**."
            )
            st.caption(
                f"Illustrative limiting vehicle capacity: {benefits.illustrative_departure_capacity} riders/departure. "
                "Potential car-trip replacement is not a measured traffic or congestion reduction. "
                "Gross car-tailpipe CO₂ excludes transit operating emissions and does not establish net savings."
            )
        else:
            st.caption("Select two transit-connected locations to explore potential benefits.")

        with st.expander("Adjust community scenario", expanded=False):
            st.caption("These inputs are hypothetical; the national reference rates are not local forecasts.")
            st.slider("Potential riders on this departure", 1, 150, 20, 1, key="community_riders")
            st.slider("Riders replacing a car trip (%)", 0, 100, 60, 5, key="community_car_share")
            st.slider("Average occupants per replaced car", 1.0, 3.0, 1.5, 0.1, key="community_occupancy")
            st.number_input("Car tailpipe kg CO₂ per mile", 0.0, 2.0, 0.40, 0.01, key="community_co2_factor")
            st.number_input("Illustrative bus capacity", 1, 300, 40, 5, key="community_bus_capacity")
            st.number_input("Illustrative rail capacity", 1, 1000, 150, 10, key="community_rail_capacity")
            st.slider("Usable onboard time (%)", 0, 100, 60, 5, key="community_usable_share",
                      help="What portion of in-vehicle time might be suitable for reading, homework or other tasks?")
            st.number_input("Maintenance, repair and tire cost ($/car mile)", 0.0, 1.0, 0.1104, 0.01,
                            key="community_maintenance_rate", format="%.4f",
                            help="AAA's 2025 US new-vehicle average is $0.1104/mile. This is a cost component, not an additional saving.")

        with st.expander("Other possible community benefits", expanded=False):
            st.markdown("""
- **Road traffic:** If transit actually replaces some car journeys, there may be fewer cars on affected roads. The estimated displaced car journeys above are not a forecast of congestion or delay reduction.
- **Noise:** Fewer car movements could lower traffic noise in some locations, but buses and trains also produce noise. No decibel reduction is calculated because sound levels depend on the existing traffic mix, speeds, location and other factors.
- **Road safety:** Reduced car travel could change collision exposure, but this model cannot estimate crashes or injuries prevented.
- **Parking:** Replacing driving trips could ease parking demand near destinations.
- **Access and flexibility:** Additional transit connections could improve access to jobs, classes and services.

These are topics for exploration, **not verified outcomes, guaranteed benefits, or official predictions**. The project neither confirms nor dismisses these possibilities; local studies would be needed to evaluate them.
""")

        with st.expander("Sources and evidence", expanded=False):
            st.markdown("""
**Published reference figures (not forecasts for this proposed network)**

- [FTA: 2024 EMBARK agency profile](https://www.transit.dot.gov/sites/fta.dot.gov/files/transit_agency_profile_doc/2024/60017.pdf) — 3,244,979 annual unlinked passenger boardings across EMBARK services. This does **not** predict ridership on a proposed line.
- [FTA: National Transit Database glossary](https://www.transit.dot.gov/ntd/national-transit-database-ntd-glossary) — boardings count each time a passenger enters a vehicle, including after transfers.
- [US DOE / 2022 National Household Travel Survey](https://www.energy.gov/cmei/vehicles/articles/fotw-1333-march-11-2024-2022-average-number-occupants-trip-household) — national average of 1.5 occupants per household vehicle trip.
- [US EPA: Typical passenger vehicle](https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle) — approximately 0.40 kg tailpipe CO₂ per mile.
- [AAA: Your Driving Costs 2025, fact sheet](https://newsroom.aaa.com/wp-content/uploads/2025/09/UPDATE-AAA-Fact-Sheet-Your-Driving-Cost-9.2025-1.pdf) — maintenance, repairs and tires averaged 11.04 cents per mile in AAA's national new-vehicle study. Not an OKC-specific cost or guaranteed cash saving.
- [FHWA: Highway traffic noise fundamentals](https://www.fhwa.dot.gov/Environment/noise/regulations_and_guidance/analysis_and_abatement_guidance/polguide01.cfm) — traffic noise uses logarithmic decibel levels; simple per-car noise subtraction is not valid.

**User-controlled assumptions:** Future riders, car-trip replacement share, capacity, usable onboard time and route distance are hypothetical. Published reference figures do not validate these inputs. The model neither endorses nor rejects possible effects and does not establish a net climate benefit, a congestion improvement, a noise reduction or prevented crashes. These results have not been approved or endorsed by ONE Transit.
""")

        with st.expander("Calculation notes and limitations", expanded=False):
            st.write("Potential replaced car journeys = hypothetical riders × replacement share ÷ car occupancy.")
            st.write("Potential replaced car miles = hypothetical replaced journeys × illustrative road distance.")
            st.write("Gross avoided car-tailpipe CO₂ = replaced car miles × kg CO₂/car mile (transit emissions excluded).")
            st.write("Possible study/reading time per rider = estimated onboard minutes × usable-time share (not a net time saving).")
            st.write("Maintenance cost component = replaced car miles × maintenance/repair/tire $ per mile (not added to existing vehicle cost comparison).")
            if trip and controller.statistics_observer.stats:
                stats = controller.statistics_observer.stats
                st.write(f"Illustrative vehicle comparison: ${stats.comparison_cost_usd:.2f}, "
                         f"{stats.comparison_minutes:.1f} minutes. "
                         f"Transit estimate: ${stats.fare_usd:.2f}, {stats.transit_minutes:.1f} minutes. "
                         "These values may be more or less favorable depending on the trip.")

st.divider()
st.caption("Sources: ONE Transit System Plan and corridor descriptions · "
           "[Discover the plan](https://www.onetransit.org/discover/) · "
           "[Official project overview](https://www.onetransit.org/projects/). "
           "Independent UCO student project; not affiliated with, approved by, or endorsed by ONE Transit. Scenario figures are not forecasts or established outcomes. Built with Python, Streamlit, Folium, NumPy, NetworkX, MVC and Observer.")
