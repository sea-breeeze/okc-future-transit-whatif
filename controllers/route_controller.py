"""Only the Controller receives UI intentions, coordinates the Model and Subject."""
import random
from models.transit_network import TransitNetwork
from models.route_calculator import TransitRouter, Itinerary
from models.statistics import ComparisonSettings
from observers.subject import TripState
from observers.map_observer import MapObserver
from observers.statistics_observer import StatisticsObserver


class RouteController:
    def __init__(self, network: TransitNetwork, *, include_local: bool = True,
                 initial_wait: float = 5, transfer_minutes: float = 7):
        self.network = network
        self.lines = network.enabled_lines(include_local=include_local)
        self.stations = network.active_stations(self.lines)
        self._router = None
        self._initial_wait = initial_wait
        self._transfer_minutes = transfer_minutes
        self.trip_state = TripState()
        self.map_observer = MapObserver()
        self.statistics_observer = StatisticsObserver(self.stations)
        self.trip_state.attach(self.map_observer)
        self.trip_state.attach(self.statistics_observer)

    @property
    def router(self):
        if self._router is None:
            self._router = TransitRouter(self.lines, transfer_minutes=self._transfer_minutes,
                                         initial_wait=self._initial_wait)
        return self._router

    def get_stations(self):
        return self.stations

    def get_lines(self):
        return self.lines

    def plan_trip(self, origin_id: str, destination_id: str,
                  settings: ComparisonSettings | None = None) -> Itinerary | None:
        itinerary = self.router.plan(origin_id, destination_id)
        # Both observers are notified, even for no-route / invalid selections.
        self.trip_state.set_trip(itinerary, settings=settings or ComparisonSettings())
        return itinerary

    def generate_random_trip(self, rng=None) -> tuple[str, str]:
        """Only return a pair with a valid transit-only path on enabled lines."""
        rng = rng or random
        candidates = list(self.stations)
        rng.shuffle(candidates)
        for start in candidates:
            destinations = [sid for sid in candidates if sid != start and self.router.reachable(start, sid)]
            if destinations:
                return start, rng.choice(destinations)
        raise ValueError("No two connected boarding points in this network")
