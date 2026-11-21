def movie_payload(title="Movie A", **overrides):
    body = {"title": title, "release_year": 2020, "runtime_minutes": 100}
    body.update(overrides)
    return body


# ----------------------------------------------------------------- movies CRUD
def test_create_movie_defaults(client):
    res = client.post("/api/movies", json=movie_payload())
    assert res.status_code == 201
    body = res.json()
    assert body["watched"] is False
    assert body["prerequisite_ids"] == []
    assert client.get("/api/movies").json() == [body]


def test_title_must_be_unique_case_insensitive(client):
    client.post("/api/movies", json=movie_payload("Iron Man"))
    res = client.post("/api/movies", json=movie_payload("  iron man "))
    assert res.status_code == 409
    assert res.json()["error"] == "DUPLICATE_TITLE"


def test_runtime_must_be_between_1_and_300(client):
    for bad in (0, 301, -5):
        res = client.post("/api/movies", json=movie_payload(runtime_minutes=bad))
        assert res.status_code == 422
        assert res.json()["error"] == "VALIDATION_ERROR"
    for ok, title in ((1, "Short"), (300, "Long")):
        assert client.post("/api/movies", json=movie_payload(title, runtime_minutes=ok)).status_code == 201


def test_unknown_prerequisite_is_rejected(client):
    res = client.post("/api/movies", json=movie_payload(prerequisite_ids=[999]))
    assert res.status_code == 422
    assert res.json()["error"] == "UNKNOWN_PREREQUISITE"


def test_patch_watched_and_fields(client):
    movie_id = client.post("/api/movies", json=movie_payload()).json()["id"]
    res = client.patch(f"/api/movies/{movie_id}", json={"watched": True, "runtime_minutes": 120})
    assert res.status_code == 200
    assert res.json()["watched"] is True
    assert res.json()["runtime_minutes"] == 120
    assert res.json()["title"] == "Movie A"  # untouched


def test_patch_rejects_null_and_missing_movie(client):
    movie_id = client.post("/api/movies", json=movie_payload()).json()["id"]
    assert client.patch(f"/api/movies/{movie_id}", json={"title": None}).status_code == 422
    assert client.patch("/api/movies/12345", json={"watched": True}).status_code == 404


def test_patch_title_to_existing_title_conflicts(client):
    client.post("/api/movies", json=movie_payload("One"))
    two = client.post("/api/movies", json=movie_payload("Two")).json()["id"]
    res = client.patch(f"/api/movies/{two}", json={"title": "one"})
    assert res.status_code == 409


def test_patch_same_title_is_allowed(client):
    movie_id = client.post("/api/movies", json=movie_payload("Same")).json()["id"]
    assert client.patch(f"/api/movies/{movie_id}", json={"title": "Same"}).status_code == 200


def test_prerequisites_can_be_changed_later(client):
    a = client.post("/api/movies", json=movie_payload("A")).json()["id"]
    b = client.post("/api/movies", json=movie_payload("B")).json()["id"]
    res = client.patch(f"/api/movies/{b}", json={"prerequisite_ids": [a]})
    assert res.json()["prerequisite_ids"] == [a]
    res = client.patch(f"/api/movies/{b}", json={"prerequisite_ids": []})
    assert res.json()["prerequisite_ids"] == []


# --------------------------------------------------------- circular dependency
def test_endgame_as_prerequisite_of_iron_man_is_409(client, sample_movies):
    res = client.patch(
        f"/api/movies/{sample_movies['Iron Man']}",
        json={"prerequisite_ids": [sample_movies["Avengers: Endgame"]]},
    )
    assert res.status_code == 409
    assert res.json()["error"] == "CIRCULAR_DEPENDENCY"


def test_direct_self_dependency_is_409(client):
    a = client.post("/api/movies", json=movie_payload("A")).json()["id"]
    res = client.patch(f"/api/movies/{a}", json={"prerequisite_ids": [a]})
    assert res.status_code == 409
    assert res.json()["error"] == "CIRCULAR_DEPENDENCY"


def test_rejected_update_changes_nothing(client, sample_movies):
    iron_man = sample_movies["Iron Man"]
    client.patch(
        f"/api/movies/{iron_man}",
        json={"prerequisite_ids": [sample_movies["Avengers: Endgame"]], "watched": True},
    )
    after = next(m for m in client.get("/api/movies").json() if m["id"] == iron_man)
    assert after["prerequisite_ids"] == []
    assert after["watched"] is False


# ---------------------------------------------------------------- rewatch order
def test_rewatch_order_for_doomsday(client, sample_movies):
    res = client.get(f"/api/movies/{sample_movies['Avengers: Doomsday']}/rewatch-order")
    assert res.status_code == 200
    body = res.json()
    ids = [m["id"] for m in body["order"]]
    others = {v for k, v in sample_movies.items() if k != "Avengers: Doomsday"}
    assert len(ids) == 7 and set(ids) == others
    pos = {i: n for n, i in enumerate(ids)}
    s = sample_movies
    assert pos[s["Iron Man"]] < pos[s["The Avengers"]]
    assert pos[s["Captain America: The First Avenger"]] < pos[s["The Avengers"]]
    assert pos[s["The Avengers"]] < pos[s["Captain America: Civil War"]]
    assert pos[s["Captain America: Civil War"]] < pos[s["Avengers: Infinity War"]]
    assert pos[s["Thor: Ragnarok"]] < pos[s["Avengers: Infinity War"]]
    assert pos[s["Avengers: Infinity War"]] < pos[s["Avengers: Endgame"]]
    assert body["total_count"] == 7
    assert body["watched_count"] == 0
    assert body["remaining_runtime_minutes"] == 126 + 124 + 143 + 147 + 130 + 149 + 181


def test_rewatch_order_civil_war(client, sample_movies):
    body = client.get(f"/api/movies/{sample_movies['Captain America: Civil War']}/rewatch-order").json()
    ids = [m["id"] for m in body["order"]]
    assert set(ids[:2]) == {sample_movies["Iron Man"], sample_movies["Captain America: The First Avenger"]}
    assert ids[2] == sample_movies["The Avengers"]
    assert len(ids) == 3


def test_rewatch_order_ragnarok_is_empty(client, sample_movies):
    body = client.get(f"/api/movies/{sample_movies['Thor: Ragnarok']}/rewatch-order").json()
    assert body["order"] == []
    assert body["total_count"] == 0
    assert body["remaining_runtime_minutes"] == 0


def test_rewatch_progress_and_remaining_time(client, sample_movies):
    for title in ("Iron Man", "The Avengers"):
        client.patch(f"/api/movies/{sample_movies[title]}", json={"watched": True})
    body = client.get(f"/api/movies/{sample_movies['Avengers: Doomsday']}/rewatch-order").json()
    assert body["watched_count"] == 2
    assert body["total_count"] == 7
    assert body["remaining_runtime_minutes"] == 124 + 147 + 130 + 149 + 181
    flags = {m["title"]: m["watched"] for m in body["order"]}
    assert flags["Iron Man"] is True and flags["Thor: Ragnarok"] is False


def test_rewatch_order_unknown_movie_is_404(client):
    assert client.get("/api/movies/999/rewatch-order").status_code == 404


# --------------------------------------------------------------------- cinemas
def test_create_and_list_cinema(client):
    res = client.post("/api/cinemas", json={"name": "Star", "bundle_sizes": [5, 2]})
    assert res.status_code == 201
    assert res.json()["bundle_sizes"] == [2, 5]
    assert len(client.get("/api/cinemas").json()) == 1


def test_cinema_validation(client):
    bad_bodies = [
        {"name": "A", "bundle_sizes": []},
        {"name": "A", "bundle_sizes": [0]},
        {"name": "A", "bundle_sizes": [501]},
        {"name": "A", "bundle_sizes": [2, 2]},
        {"name": "A", "bundle_sizes": list(range(1, 12))},
        {"name": "", "bundle_sizes": [2]},
    ]
    for body in bad_bodies:
        assert client.post("/api/cinemas", json=body).status_code == 422, body
    assert client.post("/api/cinemas", json={"name": "Ten", "bundle_sizes": list(range(1, 11))}).status_code == 201


def test_cinema_name_must_be_unique(client):
    client.post("/api/cinemas", json={"name": "Star", "bundle_sizes": [2]})
    res = client.post("/api/cinemas", json={"name": "STAR", "bundle_sizes": [3]})
    assert res.status_code == 409
    assert res.json()["error"] == "DUPLICATE_NAME"


# --------------------------------------------------------------------- booking
def make_cinema(client, sizes):
    return client.post("/api/cinemas", json={"name": f"C{sizes}", "bundle_sizes": sizes}).json()["id"]


def test_booking_examples_from_the_brief(client):
    cases = [
        ([1, 3, 4], 6, 2, {3: 2}),
        ([2, 5], 11, 4, {5: 1, 2: 3}),
        ([6, 9, 20], 44, 4, {20: 1, 9: 2, 6: 1}),
    ]
    for sizes, group, total, expected in cases:
        cid = make_cinema(client, sizes)
        res = client.get(f"/api/cinemas/{cid}/booking", params={"groupSize": group})
        assert res.status_code == 200
        body = res.json()
        assert body["possible"] is True
        assert body["total_bundles"] == total
        assert {b["size"]: b["count"] for b in body["bundles"]} == expected


def test_booking_not_possible(client):
    cid = make_cinema(client, [4, 6])
    body = client.get(f"/api/cinemas/{cid}/booking", params={"groupSize": 7}).json()
    assert body["possible"] is False
    assert body["bundles"] == []
    assert body["total_bundles"] is None
    assert "Not possible" in body["message"]


def test_booking_group_size_limits_and_unknown_cinema(client):
    cid = make_cinema(client, [2])
    for bad in (0, 10_001, -1):
        assert client.get(f"/api/cinemas/{cid}/booking", params={"groupSize": bad}).status_code == 422
    assert client.get(f"/api/cinemas/{cid}/booking").status_code == 422
    assert client.get("/api/cinemas/999/booking", params={"groupSize": 4}).status_code == 404
    assert client.get(f"/api/cinemas/{cid}/booking", params={"groupSize": 10_000}).status_code == 200
