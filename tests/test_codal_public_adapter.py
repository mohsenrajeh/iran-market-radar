import httpx
import pytest

from packages.data_adapters.codal_public import CodalPublicAdapter


def _valid_payload():
    return {
        "Total": 1,
        "Page": 1,
        "Letters": [{
            "TracingNo": 1585575,
            "Symbol": "وبملت",
            "CompanyName": "بانك ملت",
            "Title": "  اطلاعات و صورت های مالی  ",
            "PublishDateTime": "۱۴۰۵/۰۵/۲۶ ۱۵:۴۱:۵۴",
            "SentDateTime": "۱۴۰۵/۰۵/۲۶ ۱۵:۴۱:۵۴",
            "Url": "/Reports/Decision.aspx?id=1",
            "LetterCode": "ن-۱۰",
        }],
    }


@pytest.mark.asyncio
async def test_codal_search_uses_browser_contract_and_normalizes_metadata():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/search/v2/q"
        assert request.url.params["PageNumber"] == "2"
        assert request.url.params["PageSize"] == "5"
        assert request.url.params["Symbol"] == "وبملت"
        assert "Mozilla/5.0" in request.headers["user-agent"]
        return httpx.Response(200, headers={"content-type": "application/json"}, json=_valid_payload())

    adapter = CodalPublicAdapter(transport=httpx.MockTransport(handler))
    rows = await adapter.fetch_disclosures(page_number=2, page_size=5, symbol="وبملت")

    assert rows == [{
        "tracing_no": 1585575,
        "symbol": "وبملت",
        "symbol_normalized": "وبملت",
        "company_name": "بانک ملت",
        "title": "اطلاعات و صورت های مالی",
        "publish_date_time": "1405/05/26 15:41:54",
        "sent_date_time": "1405/05/26 15:41:54",
        "url": "https://codal.ir/Reports/Decision.aspx?id=1",
        "letter_code": "ن-10",
        "source": "CODAL official public search",
    }]
    assert adapter.last_total == 1
    assert adapter.last_page_count == 1
    assert adapter.independence_key == "CODAL_OFFICIAL_PUBLIC"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, headers={"content-type": "text/html"}, text="<html>blocked</html>"),
        httpx.Response(200, headers={"content-type": "application/json"}, content=b"not-json"),
        httpx.Response(200, headers={"content-type": "application/json"}, json={"Letters": []}),
        httpx.Response(200, headers={"content-type": "application/json"}, json={
            "Total": 1, "Page": 1, "Letters": [{"TracingNo": 1}],
        }),
    ],
)
async def test_codal_search_fails_closed_on_malformed_or_non_json(response):
    adapter = CodalPublicAdapter(transport=httpx.MockTransport(lambda request: response))
    assert await adapter.fetch_disclosures() == []
    assert adapter.last_error
    assert adapter.last_total is None


@pytest.mark.asyncio
async def test_codal_search_rejects_untrusted_url_and_oversize_body():
    payload = _valid_payload()
    payload["Letters"][0]["Url"] = "javascript:alert(1)"
    adapter = CodalPublicAdapter(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "application/json"}, json=payload)
    ))
    assert await adapter.fetch_disclosures() == []

    adapter = CodalPublicAdapter(
        transport=httpx.MockTransport(lambda request: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"{" + b"x" * 100 + b"}",
        )),
        max_response_bytes=50,
    )
    assert await adapter.fetch_disclosures() == []
    assert "size limit" in (adapter.last_error or "")


@pytest.mark.asyncio
async def test_codal_search_bounds_inputs_without_network_call():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_valid_payload())

    adapter = CodalPublicAdapter(transport=httpx.MockTransport(handler))
    assert await adapter.fetch_disclosures(page_number=0) == []
    assert await adapter.fetch_disclosures(page_size=101) == []
    assert await adapter.fetch_disclosures(symbol=" ") == []
    assert calls == 0
