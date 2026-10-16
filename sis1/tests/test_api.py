import pytest

from services.engagements import apply_events


@pytest.mark.parametrize("path", ["/like", "/view"])
async def test_acceptance_and_eventual_read(api, path):
    client, publisher, sessions = api
    response = await client.post("/post/", json={"content": "hello"})
    assert response.status_code == 201
    post_id = response.json()["id"]
    payload = {"post_id": post_id, "username": "alice"}
    for _ in range(2):
        response = await client.post(path, json=payload)
        assert response.status_code == 202
        assert response.json()["status"] == "accepted"
    before = (await client.get(f"/post/{post_id}")).json()
    assert before["likes_count"] == before["views_count"] == 0
    async with sessions.begin() as session:
        await apply_events(session, publisher.events)
    after = (await client.get(f"/post/{post_id}")).json()
    assert after["likes_count"] == int(path == "/like")
    assert after["views_count"] == int(path == "/view")


@pytest.mark.parametrize("path", ["/like", "/view"])
async def test_missing_post_is_not_published(api, path):
    client, publisher, _ = api
    response = await client.post(path, json={"post_id": 999999, "username": "alice"})
    assert response.status_code == 404
    assert not publisher.events


@pytest.mark.parametrize("path", ["/like", "/view"])
@pytest.mark.parametrize("payload", [{}, {"post_id": -1, "username": "a"},
                                     {"post_id": 1, "username": ""},
                                     {"post_id": 1, "username": "a" * 129},
                                     {"post_id": 1, "username": "bad\u0000name"}])
async def test_validation(api, path, payload):
    client, publisher, _ = api
    assert (await client.post(path, json=payload)).status_code == 422
    assert not publisher.events


async def test_posts_use_bounded_cursor_pagination(api):
    client, _, _ = api
    ids = []
    for _ in range(3):
        ids.append((await client.post("/post/", json={})).json()["id"])
    response = await client.get("/post/", params={"after_id": ids[0], "limit": 1})
    assert [p["id"] for p in response.json()] == [ids[1]]
    assert (await client.get("/post/", params={"limit": 101})).status_code == 422


async def test_missing_post_read(api):
    client, _, _ = api
    assert (await client.get("/post/999999")).status_code == 404
