"""Observer recomputing the trip's modeled comparison after trip state changes."""
from typing import Any
from observers.subject import Observer
from models.route_calculator import Itinerary
from models.statistics import ComparisonSettings, TripStatistics, compare_trip
from models.station import Station


class StatisticsObserver(Observer):
    def __init__(self, stations: dict[str, Station]):
        self.stations = stations
        self.stats: TripStatistics | None = None
        self.updates = 0

    def on_trip_changed(self, itinerary: Itinerary | None, **context: Any) -> None:
        settings: ComparisonSettings = context.get("settings", ComparisonSettings())
        self.stats = compare_trip(itinerary, self.stations, settings) if itinerary else None
        self.updates += 1
