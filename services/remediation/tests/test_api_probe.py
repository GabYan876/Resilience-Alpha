import json

import httpx

from app.adapters.api_probe import ApiTransactionProbe


def probe(handler, token: str = "") -> ApiTransactionProbe:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ApiTransactionProbe(client, "http://api:8000/", token)


def test_posts_test_transaction_with_bearer_token():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={"status": "settled"})

    assert probe(handler, token="abc").run()
    assert seen[0].url == "http://api:8000/transactions"
    assert seen[0].headers["authorization"] == "Bearer abc"
    payload = json.loads(seen[0].content)
    assert payload["from_account"] == "TEST-0001"
    assert payload["to_account"] == "TEST-0002"
    assert payload["amount_cents"] == 100
    assert payload["idempotency_key"].startswith("check-")


def test_rejected_transaction_fails():
    assert not probe(lambda r: httpx.Response(500)).run()


def test_non_settled_transaction_fails():
    assert not probe(lambda r: httpx.Response(201, json={"status": "pending"})).run()


def test_network_error_fails():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout")

    assert not probe(boom).run()
