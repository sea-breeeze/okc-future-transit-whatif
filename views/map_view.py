"""Folium map with locked and click-to-select modes."""
from html import escape

NETWORK_BOUNDS = [[35.10, -97.85], [35.78, -97.27]]


def build_map(stations, lines, itinerary=None, *, origin_id=None, destination_id=None,
              reveal_stations=False, zoom_to_trip=False, center=None, zoom=None,
              interactive=False):
    import folium  # Lazy: map library is not needed by routing unit tests
    from folium.plugins import Fullscreen

    m = folium.Map(location=center or [35.46, -97.52], zoom_start=zoom or 10,
                   tiles="OpenStreetMap", min_zoom=9, max_zoom=15,
                   control_scale=False, prefer_canvas=True,
                   zoom_control=interactive,
                   dragging=interactive, scroll_wheel_zoom=interactive,
                   double_click_zoom=interactive, touch_zoom=interactive,
                   box_zoom=interactive, keyboard=interactive)
    # Restrict browsing to the area around the *conceptual* transit network.
    m.options["maxBounds"] = NETWORK_BOUNDS
    m.options["maxBoundsViscosity"] = 1.0
    if interactive:
        Fullscreen(position="topright").add_to(m)

    for line in lines.values():
        folium.PolyLine(
            locations=line.path_coordinates, color=line.color,
            weight=4 if line.group == "regional" else 2.5,
            opacity=0.8 if line.group == "regional" else 0.42,
            dash_array="7,9" if line.dashed else None,
            tooltip=escape(line.name),
            smooth_factor=2.0,
            interactive=False,
        ).add_to(m)

    if itinerary:
        for leg in itinerary.legs:
            line = lines[leg.line_id]
            folium.PolyLine(leg.geometry, color="white", weight=10, opacity=0.96,
                            interactive=False).add_to(m)
            folium.PolyLine(leg.geometry, color=line.color, weight=6, opacity=1,
                            tooltip=f"Selected: {escape(line.name)}",
                            interactive=False).add_to(m)
        for sid in itinerary.transfers:
            station = stations[sid]
            folium.CircleMarker(station.coordinates, radius=9, color="#fff", weight=3,
                fill=True, fill_color="#f2a52b", fill_opacity=1,
                tooltip=f"Transfer: {escape(station.name)}",
                interactive=False).add_to(m)

    # Render only selected points, or reveal all when explicitly requested.
    visible_ids = set(stations) if (interactive or reveal_stations) else set()
    visible_ids.update(sid for sid in (origin_id, destination_id) if sid in stations)
    for sid in visible_ids:
        station = stations[sid]
        is_origin = sid == origin_id
        is_dest = sid == destination_id
        color = "#1baf88" if is_origin else "#ef6d62" if is_dest else "#2b4d85"
        folium.CircleMarker(station.coordinates, radius=11 if (is_origin or is_dest) else 7,
            color="#ffffff", weight=3 if (is_origin or is_dest) else 1.5,
            fill=True, fill_color=color, fill_opacity=1,
            tooltip=f"{'START: ' if is_origin else 'END: ' if is_dest else ''}{escape(station.name)}",
            interactive=interactive,
        ).add_to(m)

    # We don't refit on every click: doing so looks like a reset / map jump.
    if itinerary and zoom_to_trip and not center:
        path = [pt for leg in itinerary.legs for pt in leg.geometry]
        if path:
            lats = [pt[0] for pt in path]
            lons = [pt[1] for pt in path]
            m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(24, 24))
    return m
