"""Explicitly labeled what-if comparison; never creates car routes."""
from dataclasses import dataclass
from models.station import Station
from models.route_calculator import Itinerary, great_circle_miles


@dataclass(frozen=True)
class ComparisonSettings:
    fare_usd: float = 2.5
    vehicle_cost_per_mile: float = 0.67
    parking_usd: float = 2.0
    road_speed_mph: float = 31.0
    road_distance_factor: float = 1.28


@dataclass(frozen=True)
class TripStatistics:
    transit_minutes: float
    transit_miles: float
    fare_usd: float
    transfers: int
    comparison_minutes: float
    comparison_miles: float
    comparison_cost_usd: float
    money_saved_usd: float
    time_saved_minutes: float


def compare_trip(
    trip: Itinerary, stations: dict[str, Station], settings: ComparisonSettings
) -> TripStatistics:
    """Comparison is a hypothetical arithmetic benchmark, NOT driving navigation."""
    origin, destination = stations[trip.origin_id], stations[trip.destination_id]
    straight_miles = great_circle_miles(origin.coordinates, destination.coordinates)
    # This multiplier is a user-adjustable model input, not a verified road distance.
    benchmark_miles = straight_miles * settings.road_distance_factor
    benchmark_minutes = benchmark_miles / settings.road_speed_mph * 60 + 3.0
    benchmark_cost = benchmark_miles * settings.vehicle_cost_per_mile + settings.parking_usd
    return TripStatistics(
        transit_minutes=trip.minutes,
        transit_miles=trip.miles,
        fare_usd=settings.fare_usd,
        transfers=trip.transfers_count,
        comparison_minutes=benchmark_minutes,
        comparison_miles=benchmark_miles,
        comparison_cost_usd=benchmark_cost,
        money_saved_usd=benchmark_cost - settings.fare_usd,
        time_saved_minutes=benchmark_minutes - trip.minutes,
    )
