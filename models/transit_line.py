"""Proposed corridor and separate route geometry / boarding point definitions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TransitLine:
    id: str
    name: str
    color: str
    mode: str
    group: str
    speed_mph: float
    station_ids: tuple[str, ...]
    path_coordinates: tuple[tuple[float, float], ...]
    stop_indices: tuple[int, ...]
    dashed: bool = False

    def between(self, left_id: str, right_id: str) -> list[list[float]]:
        """Return the correct line geometry between *adjacent* boardable stops."""
        a = self.station_ids.index(left_id)
        b = self.station_ids.index(right_id)
        if abs(a - b) != 1:
            raise ValueError("Stops are not consecutive on this transit line")
        i, j = self.stop_indices[a], self.stop_indices[b]
        vertices = self.path_coordinates[min(i, j):max(i, j) + 1]
        if i > j:
            vertices = tuple(reversed(vertices))
        return [list(point) for point in vertices]
