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


def test_usable_time_and_maintenance_are_conditional():
    controller = RouteController(TransitNetwork(), initial_wait=2, transfer_minutes=3)
    trip = controller.plan_trip('santa_fe', 'airport')
    stats = controller.statistics_observer.stats
    result = estimate_community_benefits(trip, stats, controller.lines, BenefitAssumptions())
    assert 0 <= result.potential_usable_onboard_minutes_per_rider <= trip.minutes
    assert result.potential_maintenance_usd_avoided >= 0
    no_benefits = estimate_community_benefits(trip, stats, controller.lines,
        BenefitAssumptions(usable_onboard_time_share=0, car_trip_replacement_share=0))
    assert no_benefits.potential_usable_onboard_minutes_per_rider == 0
    assert no_benefits.potential_maintenance_usd_avoided == 0


def test_usable_time_does_not_count_wait_or_transfers():
    controller = RouteController(TransitNetwork(), initial_wait=8, transfer_minutes=12)
    trip = controller.plan_trip('santa_fe', 'airport')
    stats = controller.statistics_observer.stats
    result = estimate_community_benefits(trip, stats, controller.lines,
        BenefitAssumptions(usable_onboard_time_share=1.0))
    assert abs(result.potential_usable_onboard_minutes_per_rider - sum(leg.minutes for leg in trip.legs)) < 1e-8
