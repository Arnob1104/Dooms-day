import pytest

from app.algorithms import CycleError, creates_cycle, min_bundles, rewatch_order

# ------------------------------------------------------------------ helpers
# ids: 1 Iron Man, 2 First Avenger, 3 Avengers, 4 Civil War, 5 Ragnarok,
#      6 Infinity War, 7 Endgame, 8 Doomsday
GRAPH = {3: [1, 2], 4: [3], 6: [4, 5], 7: [6], 8: [7]}


def assert_valid_order(order: list[int], graph: dict[int, list[int]]) -> None:
    position = {m: i for i, m in enumerate(order)}
    assert len(position) == len(order), "a movie appears twice"
    for movie in order:
        for prereq in graph.get(movie, []):
            assert prereq in position, f"{prereq} missing from order"
            assert position[prereq] < position[movie], f"{prereq} must come before {movie}"


# ---------------------------------------------------------- rewatch order
def test_rewatch_doomsday_has_all_seven_others():
    order = rewatch_order(8, GRAPH)
    assert sorted(order) == [1, 2, 3, 4, 5, 6, 7]
    assert 8 not in order
    assert_valid_order(order, GRAPH)


def test_rewatch_civil_war():
    order = rewatch_order(4, GRAPH)
    assert sorted(order[:2]) == [1, 2]
    assert order[2] == 3
    assert len(order) == 3


def test_rewatch_ragnarok_is_empty():
    assert rewatch_order(5, GRAPH) == []


def test_rewatch_diamond_lists_shared_prerequisite_once():
    graph = {4: [2, 3], 2: [1], 3: [1]}
    order = rewatch_order(4, graph)
    assert sorted(order) == [1, 2, 3]
    assert_valid_order(order, graph)


def test_rewatch_long_chain_does_not_hit_recursion_limit():
    n = 20_000
    graph = {i: [i - 1] for i in range(1, n)}
    order = rewatch_order(n - 1, graph)
    assert order == list(range(0, n - 1))


def test_rewatch_raises_on_corrupt_cyclic_data():
    with pytest.raises(CycleError):
        rewatch_order(1, {1: [2], 2: [3], 3: [1]})


# ------------------------------------------------------------ cycle check
def test_brief_example_endgame_as_prerequisite_of_iron_man_is_a_cycle():
    assert creates_cycle(1, [7], GRAPH) is True


def test_self_dependency_is_a_cycle():
    assert creates_cycle(5, [5], GRAPH) is True


def test_two_step_cycle():
    assert creates_cycle(1, [2], {2: [1]}) is True


def test_valid_new_prerequisite_is_not_a_cycle():
    assert creates_cycle(5, [1], GRAPH) is False  # Ragnarok after Iron Man is fine


def test_diamond_shape_is_not_a_cycle():
    assert creates_cycle(4, [2, 3], {2: [1], 3: [1]}) is False


def test_old_prerequisites_of_the_movie_are_ignored():
    # 4 currently needs 3; replacing that with [1] must not be blocked by 4 -> 3 -> ... -> 4
    assert creates_cycle(4, [1], GRAPH) is False


def test_empty_prerequisites_never_cycle():
    assert creates_cycle(1, [], GRAPH) is False


# ------------------------------------------------------- booking (coin change)
def as_dict(result):
    return None if result is None else {b.size: b.count for b in result}


def test_booking_1_3_4_for_6_is_two_threes():
    result = min_bundles([1, 3, 4], 6)
    assert as_dict(result) == {3: 2}
    assert sum(b.count for b in result) == 2


def test_booking_2_5_for_11():
    result = min_bundles([2, 5], 11)
    assert as_dict(result) == {5: 1, 2: 3}
    assert sum(b.count for b in result) == 4


def test_booking_6_9_20_for_44():
    result = min_bundles([6, 9, 20], 44)
    assert as_dict(result) == {20: 1, 9: 2, 6: 1}
    assert sum(b.count for b in result) == 4


def test_booking_4_6_for_7_is_not_possible():
    assert min_bundles([4, 6], 7) is None


def test_booking_result_always_adds_up_exactly():
    for sizes, group in [([7, 13, 29], 500), ([3, 11], 10_000), ([1], 10_000), ([500], 10_000)]:
        result = min_bundles(sizes, group)
        assert result is not None
        assert sum(b.size * b.count for b in result) == group


def test_booking_greedy_would_fail_but_dp_is_optimal():
    # Greedy takes 4+1+1 = 3 bundles for 6; optimal is 3+3 = 2 bundles.
    assert sum(b.count for b in min_bundles([1, 3, 4], 6)) == 2


def test_booking_single_seat_and_exact_bundle():
    assert as_dict(min_bundles([5, 2], 5)) == {5: 1}
    assert as_dict(min_bundles([1], 1)) == {1: 1}


def test_booking_max_group_size_is_fast():
    assert min_bundles([2, 3, 499, 500, 487, 123, 17, 9, 41, 250], 10_000) is not None


def test_booking_unsorted_sizes_work():
    assert as_dict(min_bundles([5, 2], 11)) == {5: 1, 2: 3}
