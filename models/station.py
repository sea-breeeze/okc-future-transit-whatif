"""A location at which a rider can board within this *conceptual* network."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    latitude: float
    longitude: float
    note: str = "Illustrative boarding point; verify before real travel."

    @property
    def coordinates(self) -> list[float]:
        return [self.latitude, self.longitude]
