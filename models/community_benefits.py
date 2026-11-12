"""What-if community benefits, not measured outcomes or verified forecasts."""
from dataclasses import dataclass
from models.route_calculator import Itinerary
from models.statistics import TripStatistics


@dataclass(frozen=True)
class BenefitAssumptions:
    potential_passengers: int = 20
    car_trip_replacement_share: float = 0.60
    average_car_occupancy: float = 1.50
    tailpipe_kg_co2_per_car_mile: float = 0.40
    illustrative_bus_capacity: int = 40
    illustrative_rail_capacity: int = 150


@dataclass(frozen=True)
class CommunityBenefits:
    potential_passengers: int
    illustrative_departure_capacity: int
    potential_displaced_car_trips: float
    potential_displaced_car_miles: float
    potential_gross_tailpipe_co2_kg: float


def estimate_community_benefits(
    trip: Itinerary, stats: TripStatistics, lines: dict,
    assumptions: BenefitAssumptions,
) -> CommunityBenefits:
    """Scenario only. Gross car tailpipe reduction, not net life-cycle CO2.

    The limiting capacity among the services in a multi-leg trip defines a
    *hypothetical* per-departure capacity, not available seats or ridership.
    """
    modes = [lines[leg.line_id].mode.lower() for leg in trip.legs]
    capacities = [
        assumptions.illustrative_rail_capacity if 'rail' in mode
        else assumptions.illustrative_bus_capacity
        for mode in modes
    ]
    capacity = min(capacities) if capacities else 0
    riders = max(0, min(assumptions.potential_passengers, capacity))
    share = min(1.0, max(0.0, assumptions.car_trip_replacement_share))
    occupancy = max(1.0, assumptions.average_car_occupancy)
    displaced_trips = riders * share / occupancy
    displaced_miles = displaced_trips * max(0.0, stats.comparison_miles)
    kg = displaced_miles * max(0.0, assumptions.tailpipe_kg_co2_per_car_mile)
    return CommunityBenefits(
        potential_passengers=riders,
        illustrative_departure_capacity=capacity,
        potential_displaced_car_trips=displaced_trips,
        potential_displaced_car_miles=displaced_miles,
        potential_gross_tailpipe_co2_kg=kg,
    )
