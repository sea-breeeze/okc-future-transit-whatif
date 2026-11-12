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
st.set_page_config(page_title="OKC Future Transit Explorer — Student Concept Project", page_icon="",
                   layout="wide", initial_sidebar_state="expanded")
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
        return (0, "⇄ Transfer hub")
    if "Commuter rail" in services or "Light rail" in services:
        return (1, " Rail")
    if "Bus rapid transit" in services:
        return (2, " Rapid bus")
    return (3, "🚏 Local bus")


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
  <div class="hero-kicker">INDEPENDENT STUDENT PROJECT</div>
  <div class="hero-title">OKC Future Transit Explorer</div>
  <div class="hero-desc">
    Explore conceptual transit connections across Central Oklahoma.
    Plan hypothetical journeys and visualize potential community benefits.
  </div>
</section>
''', unsafe_allow_html=True)

st.info(
    "Independent educational project developed by a UCO student. "
    "Not affiliated with, endorsed by, or approved by ONE Transit. "
    "Routes, stations, travel times, and community estimates are "
    "illustrative and are not official plans or forecasts."
)

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
                "warning": "Concept network; all travel times, routes and fares are illustrative."
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
        "🔒 Map locked · use Starting point / Destination above."
        if not map_interactive else
        "✳ Map active · drag to move; click a circle for START, then another for DESTINATION. Next circle begins a new trip."
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
            map_widget, height=460, use_container_width=True,
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
        components.html(map_widget.get_root().render(), height=460, scrolling=False)

    with st.expander("Map legend", expanded=False):
        st.markdown('<div class="line-key">'
                    '<span><i style="background:#18af92"></i>Start</span>'
                    '<span><i style="background:#f07166"></i>Destination</span>'
                    '<span><i style="background:#f0ad38"></i>Transfer</span>'
                    '<span><i style="background:#355ed0"></i>Selected transit route</span>'
                    '</div>', unsafe_allow_html=True)
        st.warning(
                "Conceptual network: Station locations, route alignments, "
                "travel times, and connections are approximations created "
                "for educational simulation. Do not use this map for actual travel."
            )
                    
    st.markdown('<div class="section-head">Trip at a glance</div>', unsafe_allow_html=True)
    st.markdown(kpi_html(controller.statistics_observer.stats, show_comparison),
                unsafe_allow_html=True)
    st.markdown('<div class="footnote">All routes are simplified conceptual alignments based on '
                'the user-provided future-system map and the ONE Transit corridor descriptions. '
                'Pins are not verified stops; durations, frequencies, fares, and savings are simulations.</div>',
                unsafe_allow_html=True)

with benefits_col:
    st.markdown('<div class="section-head">Community outlook</div>', unsafe_allow_html=True)
    # Conservative, clearly conditional community scenario; nothing here is
    # an observed reduction or a claim that an actual accident was prevented.
    with st.expander("Potential community benefits · what-if scenario", expanded=True):
        with st.expander("Adjust community scenario", expanded=False):
            st.caption("Editable assumptions. These are not measured future-network forecasts.")
            passenger_scenario = st.slider("Potential riders on this departure", 1, 150, 20, 1)
            replacement_share = st.slider("Riders replacing a car trip (%)", 0, 100, 60, 5)
            average_occupancy = st.slider("Average occupants per replaced car", 1.0, 3.0, 1.5, 0.1)
            co2_factor = st.number_input("Car tailpipe kg CO₂ per mile", 0.0, 2.0, 0.40, 0.01)
            bus_capacity = st.number_input("Illustrative bus capacity", 1, 300, 40, 5)
            rail_capacity = st.number_input("Illustrative rail capacity", 1, 1000, 150, 10)
        if trip and controller.statistics_observer.stats:
            stats = controller.statistics_observer.stats
            assumptions = BenefitAssumptions(
                potential_passengers=passenger_scenario,
                car_trip_replacement_share=replacement_share / 100,
                average_car_occupancy=average_occupancy,
                tailpipe_kg_co2_per_car_mile=co2_factor,
                illustrative_bus_capacity=bus_capacity,
                illustrative_rail_capacity=rail_capacity,
            )
            benefits = estimate_community_benefits(trip, stats, lines, assumptions)
            st.caption("Illustrative **per departure** scenario, not an official forecast or measured impact. Passenger counts and vehicle capacities are user-selected, not predictions.")
            st.metric("Potential riders", f"{benefits.potential_passengers:,}")
            st.metric("Car miles potentially replaced", f"{benefits.potential_displaced_car_miles:,.1f} mi")
            st.metric("Gross car tailpipe CO₂ potentially avoided", f"{benefits.potential_gross_tailpipe_co2_kg:,.1f} kg")
            st.caption(
                f"Example limiting vehicle capacity: {benefits.illustrative_departure_capacity} riders/departure; "
                f"roughly {benefits.potential_displaced_car_trips:.1f} car journeys could be displaced "
                "under the chosen assumptions. This does **not** subtract transit emissions, "
                "account for vehicle manufacturing, or establish net climate benefits."
            )
            with st.expander("Sources and evidence", expanded=False):
                st.markdown("""
**Measured regional context (not a prediction for this future route)**

- [FTA: 2024 EMBARK agency profile](https://www.transit.dot.gov/sites/fta.dot.gov/files/transit_agency_profile_doc/2024/60017.pdf) — 3,244,979 reported annual unlinked passenger boardings across EMBARK services. This does **not** establish riders on a proposed line or departure.
- [FTA: National Transit Database terminology](https://www.transit.dot.gov/ntd/national-transit-database-ntd-glossary) — a boarding is counted each time someone enters a transit vehicle; transfers may count more than once.
- [US Department of Energy / 2022 NHTS](https://www.energy.gov/cmei/vehicles/articles/fotw-1333-march-11-2024-2022-average-number-occupants-trip-household) — 1.5 average people per US household-vehicle trip; national baseline, not a measured OKC trip occupancy.
- [US EPA: Typical passenger vehicle](https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle) — approximately 400 grams of tailpipe CO₂ per mile for a typical passenger vehicle, equivalent to the default 0.40 kg/mile assumption.

**Not independently established:** 20 riders per departure, 60% car-trip replacement, 40 bus / 150 rail capacity. These are editable *what-if* inputs, not facts about the planned system. The CO₂ figure is **gross avoided car tailpipe emissions only**; it excludes emissions from operating transit and cannot be interpreted as net savings. No reliable number of prevented accidents can be inferred from this model.
""")
            with st.expander("Other possible benefits · qualitative notes", expanded=False):
                st.markdown("""
- **Potential safety benefit:** Fewer car journeys could reduce exposure to roadway collisions. No specific crashes prevented can be predicted or claimed from one trip.
- **Less parking demand:** Trips replacing driving could reduce the number of parked cars needed near destinations.
- **Improved access:** More travel options could connect people with jobs, classes, and services.
- **More choice:** Transfer links could offer a travel alternative for people who cannot or prefer not to drive.

These are possibilities, **not guaranteed outcomes**, quantified accident reductions, or statements of project effectiveness.
""")
            with st.expander("Calculation notes and limitations", expanded=False):
                st.write("Car trips replaced = potential riders × car-trip-replacement share ÷ car occupancy.")
                st.write("Car miles replaced = estimated replaced trips × illustrative road distance.")
                st.write("Gross avoided tailpipe CO₂ = estimated replaced car miles × illustrative kg CO₂/mile.")
                st.write("These assumptions don't establish actual ridership, road safety outcomes, or net emissions savings.")
                st.write(f"Illustrative vehicle comparison: ${stats.comparison_cost_usd:.2f}, "
                         f"{stats.comparison_minutes:.1f} minutes. "
                         f"Transit estimate: ${stats.fare_usd:.2f}, {stats.transit_minutes:.1f} minutes. "
                         "These values may be more or less favorable depending on the trip.")
        else:
            st.caption("Select two transit-connected locations to explore potential benefits.")

st.divider()
st.caption("Sources: ONE Transit System Plan and corridor descriptions · "
           "[Discover the plan](https://www.onetransit.org/discover/) · "
           "[Official project overview](https://www.onetransit.org/projects/). "
           "Not affiliated with ONE Transit. Built with Python, Streamlit, Folium, NumPy, NetworkX, MVC and Observer.")
