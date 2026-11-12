"""Load and validate the editable, illustrative network JSON."""
import json
from pathlib import Path
from models.station import Station
from models.transit_line import TransitLine

BASE = Path(__file__).resolve().parents[1]


class TransitNetwork:
    def __init__(self, data_dir: Path | None = None):
        folder = Path(data_dir) if data_dir else BASE / "data"
        with (folder / "stations.json").open(encoding="utf-8") as handle:
            station_data = json.load(handle)
        with (folder / "routes.json").open(encoding="utf-8") as handle:
            route_data = json.load(handle)

        self.stations: dict[str, Station] = {}
        for record in station_data:
            station = Station(
                id=record["id"], name=record["name"],
                latitude=float(record["latitude"]),
                longitude=float(record["longitude"]),
                note=record.get("note", "Approximate concept stop."),
            )
            if station.id in self.stations:
                raise ValueError(f"Duplicate station ID: {station.id}")
            self.stations[station.id] = station

        self.lines: dict[str, TransitLine] = {}
        for item in route_data:
            line = TransitLine(
                id=item["id"], name=item["name"], color=item["color"],
                mode=item["mode"], group=item["group"],
                speed_mph=float(item["speed_mph"]),
                station_ids=tuple(item["station_ids"]),
                path_coordinates=tuple(tuple(map(float, p)) for p in item["path_coordinates"]),
                stop_indices=tuple(int(n) for n in item["stop_indices"]),
                dashed=item.get("dashed", False),
            )
            self._validate(line)
            if line.id in self.lines:
                raise ValueError(f"Duplicate line ID: {line.id}")
            self.lines[line.id] = line

    def _validate(self, line: TransitLine) -> None:
        if len(line.station_ids) < 2 or len(line.station_ids) != len(line.stop_indices):
            raise ValueError(f"Bad stop list or indices for {line.name}")
        if len(set(line.station_ids)) != len(line.station_ids):
            raise ValueError(f"Repeated stops on {line.name}")
        if line.speed_mph <= 0:
            raise ValueError(f"Speed must be positive: {line.name}")
        if any(s not in self.stations for s in line.station_ids):
            raise ValueError(f"Unknown station on {line.name}")
        if sorted(line.stop_indices) != list(line.stop_indices):
            raise ValueError(f"Indices must increase for {line.name}")
        if not line.path_coordinates or line.stop_indices[-1] >= len(line.path_coordinates):
            raise ValueError(f"Incomplete shape for {line.name}")
        for stop_id, index in zip(line.station_ids, line.stop_indices):
            station = self.stations[stop_id]
            lat, lon = line.path_coordinates[index]
            if abs(lat-station.latitude)>1e-5 or abs(lon-station.longitude)>1e-5:
                raise ValueError(f"Stop {stop_id} not aligned with geometry of {line.name}")

    def enabled_lines(self, include_local: bool = True) -> dict[str, TransitLine]:
        return {
            key: line for key, line in self.lines.items()
            if include_local or line.group == "regional"
        }

    def active_stations(self, enabled_lines: dict[str, TransitLine]) -> dict[str, Station]:
        ids = {sid for line in enabled_lines.values() for sid in line.station_ids}
        return {sid: station for sid, station in self.stations.items() if sid in ids}
