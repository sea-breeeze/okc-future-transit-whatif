"""Explicit Observer pattern. Stateful subjects broadcast events to registered observers."""
from abc import ABC, abstractmethod
from typing import Any
from models.route_calculator import Itinerary


class Observer(ABC):
    @abstractmethod
    def on_trip_changed(self, itinerary: Itinerary | None, **context: Any) -> None:
        pass


class TripState:
    def __init__(self) -> None:
        self._observers: list[Observer] = []
        self.itinerary: Itinerary | None = None

    def attach(self, observer: Observer) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def set_trip(self, itinerary: Itinerary | None, **context: Any) -> None:
        self.itinerary = itinerary
        for observer in tuple(self._observers):
            observer.on_trip_changed(itinerary, **context)
