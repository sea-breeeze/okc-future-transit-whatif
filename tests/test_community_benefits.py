from controllers.route_controller import RouteController
from models.transit_network import TransitNetwork
from models.community_benefits import BenefitAssumptions, estimate_community_benefits


def test_scenario_is_nonnegative_and_capped_by_example_capacity():
    controller = RouteController(TransitNetwork(), initial_wait=2, transfer_minutes=3)
    itinerary = controller.plan_trip('santa_fe', 'airport')
    stat = controller.statistics_observer.stats
    result = estimate_community_benefits(itinerary, stat, controller.lines,
        BenefitAssumptions(potential_passengers=500, illustrative_rail_capacity=90))
    assert result.potential_passengers == 90
    assert result.potential_gross_tailpipe_co2_kg >= 0
    assert result.potential_displaced_car_miles >= 0


def test_no_replacement_means_no_avoided_tailpipe_co2():
    controller = RouteController(TransitNetwork())
    itinerary = controller.plan_trip('santa_fe', 'airport')
    stat = controller.statistics_observer.stats
    result = estimate_community_benefits(itinerary, stat, controller.lines,
        BenefitAssumptions(car_trip_replacement_share=0))
    assert result.potential_gross_tailpipe_co2_kg == 0
    assert result.potential_displaced_car_trips == 0
