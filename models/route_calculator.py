"""Transfer-aware route search restricted to explicitly defined transit edges.

The graph NEVER contains car roads, walking shortcuts or implicit lines between
nearby but unconnected stations. A transfer is only allowed at the SAME stop ID.
"""
from dataclasses import dataclass
from typing import Optional
from models.transit_line import TransitLine


def great_circle_miles(a, b) -> float:
    """NumPy spherical distance (scalar output); imported only when needed."""
    import numpy as np
    endpoints = np.radians(np.asarray([a, b], dtype=np.float64))
    dlat, dlon = endpoints[1] - endpoints[0]
    h = np.sin(dlat / 2) ** 2 + np.cos(endpoints[0, 0]) * np.cos(endpoints[1, 0]) * np.sin(dlon / 2) ** 2
    return float(3958.7613 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1))))


def geometry_miles(points) -> float:
    """Calculate all segment lengths at once instead of looping in Python."""
    import numpy as np
    p = np.radians(np.asarray(points, dtype=np.float64))
    if len(p) < 2:
        return 0.0
    a, b = p[:-1], p[1:]
    delta = b - a
    h = np.sin(delta[:, 0] / 2) ** 2 + np.cos(a[:, 0]) * np.cos(b[:, 0]) * np.sin(delta[:, 1] / 2) ** 2
    return float(np.sum(3958.7613 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))))


def nearest_station_id(position, stations, max_distance_miles=0.9):
    """Vectorized selection; no station markers need to be created first."""
    import numpy as np
    if not stations:
        return None
    ids = tuple(stations)
    coords = np.radians(np.asarray([stations[i].coordinates for i in ids], dtype=np.float64))
    position = np.radians(np.asarray(position, dtype=np.float64))
    delta = coords - position
    h = np.sin(delta[:, 0] / 2) ** 2 + np.cos(position[0]) * np.cos(coords[:, 0]) * np.sin(delta[:, 1] / 2) ** 2
    miles = 3958.7613 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
    index = int(np.argmin(miles))
    return ids[index] if miles[index] <= max_distance_miles else None


@dataclass(frozen=True)
class Leg:
    line_id: str
    from_id: str
    to_id: str
    minutes: float
    miles: float
    geometry: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class Itinerary:
    origin_id: str
    destination_id: str
    legs: tuple[Leg, ...]
    minutes: float
    miles: float
    transfers: tuple[str, ...]
    stops: tuple[str, ...]

    @property
    def transfers_count(self) -> int:
        return len(self.transfers)


class TransitRouter:
    def __init__(self, lines: dict[str, TransitLine], transfer_minutes: float = 7.0, initial_wait: float = 5.0):
        self.lines = lines
        self.transfer_minutes = transfer_minutes
        self.initial_wait = initial_wait
        import networkx as nx  # Delayed until a route is requested
        self.graph = nx.DiGraph()
        self.station_lines: dict[str, set[str]] = {}
        self._build()

    def _build(self) -> None:
        for line in self.lines.values():
            for sid in line.station_ids:
                self.station_lines.setdefault(sid, set()).add(line.id)
                self.graph.add_node((sid, line.id))
            for a, b in zip(line.station_ids, line.station_ids[1:]):
                coords = line.between(a, b)
                miles = geometry_miles(coords)
                minutes = (miles / line.speed_mph) * 60 + 0.7
                self.graph.add_edge((a, line.id), (b, line.id), weight=minutes,
                    kind="ride", line_id=line.id, miles=miles, geometry=coords)
                self.graph.add_edge((b, line.id), (a, line.id), weight=minutes,
                    kind="ride", line_id=line.id, miles=miles, geometry=list(reversed(coords)))
        for sid, line_ids in self.station_lines.items():
            for a in line_ids:
                for b in line_ids:
                    if a != b:
                        self.graph.add_edge((sid, a), (sid, b), weight=self.transfer_minutes,
                                            kind="transfer", station_id=sid)

    def reachable(self, origin_id: str, destination_id: str) -> bool:
        if origin_id == destination_id:
            return False
        if origin_id not in self.station_lines or destination_id not in self.station_lines:
            return False
        return self.plan(origin_id, destination_id) is not None

    def plan(self, origin_id: str, destination_id: str) -> Optional[Itinerary]:
        if origin_id == destination_id:
            return None
        if origin_id not in self.station_lines or destination_id not in self.station_lines:
            return None
        # A synthetic SOURCE can enter only real transit lines at the selected
        # origin; the synthetic SINK can exit only at the destination.
        graph = self.graph.copy()
        src, dst = ("__origin__", "__origin__"), ("__destination__", "__destination__")
        for lid in self.station_lines[origin_id]:
            graph.add_edge(src, (origin_id, lid), weight=self.initial_wait, kind="wait")
        for lid in self.station_lines[destination_id]:
            graph.add_edge((destination_id, lid), dst, weight=0, kind="arrive")
        import networkx as nx
        try:
            path = nx.shortest_path(graph, src, dst, weight="weight")
        except nx.NetworkXNoPath:
            return None

        # Adjacent ride edges on the same line are combined into one readable leg.
        steps = []
        transfers = []
        stops = [origin_id]
        minutes = 0.0
        for u, v in zip(path, path[1:]):
            edge = graph[u][v]
            minutes += edge["weight"]
            if edge["kind"] == "transfer":
                transfers.append(edge["station_id"])
            if edge["kind"] == "ride":
                steps.append((u[0], v[0], edge))
                stops.append(v[0])

        legs = []
        for a, b, edge in steps:
            if legs and legs[-1].line_id == edge["line_id"] and legs[-1].to_id == a:
                previous = legs[-1]
                # Avoid duplicating the shared coordinate at the join.
                geometry = previous.geometry + tuple(tuple(p) for p in edge["geometry"][1:])
                legs[-1] = Leg(previous.line_id, previous.from_id, b,
                               previous.minutes + edge["weight"], previous.miles + edge["miles"], geometry)
            else:
                legs.append(Leg(edge["line_id"], a, b, edge["weight"], edge["miles"],
                                tuple(tuple(p) for p in edge["geometry"])))
        return Itinerary(origin_id, destination_id, tuple(legs), minutes,
                         sum(leg.miles for leg in legs), tuple(transfers), tuple(stops))
