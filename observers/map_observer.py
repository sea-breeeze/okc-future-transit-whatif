"""Observer holding map presentation state, without depending on Streamlit."""
from typing import Any
from observers.subject import Observer
from models.route_calculator import Itinerary


class MapObserver(Observer):
    def __init__(self):
        self.selected_itinerary: Itinerary | None = None
        self.updates = 0

    def on_trip_changed(self, itinerary: Itinerary | None, **context: Any) -> None:
        self.selected_itinerary = itinerary
        self.updates += 1
