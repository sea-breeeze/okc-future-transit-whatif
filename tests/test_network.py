"""Run from the project root: python -m pytest -q"""
import pytest
from controllers.route_controller import RouteController
from models.transit_network import TransitNetwork
from models.route_calculator import great_circle_miles
from models.statistics import ComparisonSettings


@pytest.fixture(scope="module")
def network():
    return TransitNetwork()


def test_data_loads_and_geometry_is_anchored(network):
    assert len(network.lines) == 10
    assert len(network.stations) == 32
    for line in network.lines.values():
        assert line.path_coordinates[line.stop_indices[0]] == tuple(network.stations[line.station_ids[0]].coordinates)
        assert line.path_coordinates[line.stop_indices[-1]] == tuple(network.stations[line.station_ids[-1]].coordinates)
        for a, b in zip(line.station_ids, line.station_ids[1:]):
            assert line.between(a, b)[0] == network.stations[a].coordinates
            assert line.between(a, b)[-1] == network.stations[b].coordinates
            assert line.between(b, a)[0] == network.stations[b].coordinates


def test_transit_only_transfer_avoids_road_shortcuts(network):
    controller = RouteController(network, include_local=False)
    trip = controller.plan_trip("edmond_central", "airport")
    assert trip is not None
    assert [leg.line_id for leg in trip.legs] == ["commuter", "airport_rail"]
    assert trip.transfers == ("santa_fe",)
    assert all(leg.line_id in controller.lines for leg in trip.legs)
    assert all(leg.geometry[0] == tuple(controller.stations[leg.from_id].coordinates) for leg in trip.legs)


def test_campus_requires_local_connector(network):
    core = RouteController(network, include_local=False)
    assert core.plan_trip("uco", "airport") is None
    full = RouteController(network, include_local=True)
    trip = full.plan_trip("uco", "airport")
    assert trip is not None
    assert trip.legs[0].line_id == "citylink"
    assert trip.legs[-1].line_id == "airport_rail"


def test_swapped_route_is_valid(network):
    c = RouteController(network, include_local=True)
    there = c.plan_trip("uco", "tinker")
    back = c.plan_trip("tinker", "uco")
    assert there and back
    assert abs(there.miles - back.miles) < .001
    assert abs(there.minutes - back.minutes) < .001


def test_no_route_to_same_station(network):
    c = RouteController(network)
    assert c.plan_trip("santa_fe", "santa_fe") is None
    assert c.map_observer.selected_itinerary is None
    assert c.statistics_observer.stats is None


def test_only_ride_or_transfer_edges(network):
    c = RouteController(network)
    kinds = {edge["kind"] for _, _, edge in c.router.graph.edges(data=True)}
    assert kinds == {"ride", "transfer"}
    # A nearby pair which lacks a common ID cannot transfer unless explicit edges exist.
    for a, b, data in c.router.graph.edges(data=True):
        if data["kind"] == "transfer":
            assert a[0] == b[0]
        else:
            assert a[1] == b[1]


def test_random_trip_is_distinct_and_connected(network):
    c = RouteController(network, include_local=False)
    for _ in range(12):
        start, end = c.generate_random_trip()
        assert start != end
        assert c.router.reachable(start, end)


def test_observers_are_really_notified(network):
    c = RouteController(network)
    assert c.map_observer.updates == 0
    assert c.statistics_observer.updates == 0
    c.plan_trip("santa_fe", "airport")
    assert c.map_observer.updates == 1
    assert c.statistics_observer.updates == 1
    assert c.statistics_observer.stats is not None
    c.trip_state.detach(c.map_observer)
    c.plan_trip("santa_fe", "tinker")
    assert c.map_observer.updates == 1
    assert c.statistics_observer.updates == 2


def test_financial_assumptions_update_savings(network):
    c = RouteController(network)
    c.plan_trip("santa_fe", "airport", ComparisonSettings(fare_usd=2.5))
    original = c.statistics_observer.stats.money_saved_usd
    c.plan_trip("santa_fe", "airport", ComparisonSettings(fare_usd=5.0))
    assert c.statistics_observer.stats.money_saved_usd == pytest.approx(original - 2.5)


def test_distance_reasonable():
    assert great_circle_miles([35.4653,-97.5149],[35.4653,-97.5149]) == 0
    assert 4 < great_circle_miles([35.4653,-97.5149],[35.3931,-97.6007]) < 8
