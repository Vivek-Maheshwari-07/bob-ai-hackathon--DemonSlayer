"""Tests for the Live openFDA Lookup (Module M2 dynamic-proof feature).

Mocks httpx.Client.get so these tests never depend on real network access,
covering the happy path, the "too few reports" graceful degrade, and the
network-failure fallback.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient, TimeoutException

from app.main import app
from app.m2_prr.live_openfda import lookup_live_signal


def _mock_response(total: int = 0, results=None, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = (
        {"results": results} if results is not None
        else {"meta": {"results": {"total": total}}}
    )
    return resp


def test_live_lookup_happy_path_mocked():
    """Happy path: drug_total, event_total, drug_event, grand_total all resolve to a real SIGNAL."""
    responses = [
        _mock_response(total=44279),   # n_drug_total
        _mock_response(total=173520),  # n_event_total
        _mock_response(total=17938),   # n_drug_event
        _mock_response(total=20692690),  # n_total
    ]
    with patch("httpx.Client.get", side_effect=responses):
        result = lookup_live_signal("ROFECOXIB", "MYOCARDIAL INFARCTION")

    assert result["success"] is True
    assert result["source"] == "LIVE_OPENFDA_API"
    assert result["drug_name"] == "ROFECOXIB"
    assert result["event_term"] == "MYOCARDIAL INFARCTION"
    assert result["signal_status"] == "SIGNAL"
    assert result["is_signal"] is True
    assert result["metrics"]["prr"] > 2.0
    assert result["contingency_table"]["a_drug_event"] == 17938


def test_live_lookup_not_enough_data():
    """Drug exists but the drug+event pair has too few co-reported cases for a reliable signal."""
    responses = [
        _mock_response(total=500),   # n_drug_total (drug exists)
        _mock_response(total=1000),  # n_event_total
        _mock_response(total=1),     # n_drug_event -- below DEFAULT_MIN_CASES (3)
        _mock_response(total=20692690),  # n_total
    ]
    with patch("httpx.Client.get", side_effect=responses):
        result = lookup_live_signal("SOMEDRUG", "RARE EVENT")

    assert result["success"] is False
    assert "too few" in result["error"].lower() or "minimum" in result["error"].lower()
    assert result["n_drug_event"] == 1


def test_live_lookup_network_failure_graceful():
    """openFDA unreachable/timeout must degrade gracefully, never raise or 500."""
    with patch("httpx.Client.get", side_effect=TimeoutException("timed out")):
        result = lookup_live_signal("ANYDRUG", "ANYEVENT")

    assert result["success"] is False
    assert "timed out" in result["error"].lower()


def test_live_lookup_drug_not_found():
    """A drug with zero openFDA reports should be a clean success=False, not an exception."""
    with patch("httpx.Client.get", return_value=_mock_response(total=0, status_code=404)):
        result = lookup_live_signal("ZZZNOTADRUGXYZ")

    assert result["success"] is False
    assert "no openfda" in result["error"].lower()


@pytest.mark.asyncio
async def test_live_lookup_endpoint_returns_200_on_success():
    """The API endpoint should return HTTP 200 with the structured envelope, even on failure cases."""
    responses = [
        _mock_response(total=44279),
        _mock_response(total=173520),
        _mock_response(total=17938),
        _mock_response(total=20692690),
    ]
    with patch("httpx.Client.get", side_effect=responses):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/signals/live-lookup",
                json={"drug_name": "ROFECOXIB", "event_term": "MYOCARDIAL INFARCTION"},
            )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["signal_status"] == "SIGNAL"


@pytest.mark.asyncio
async def test_live_lookup_endpoint_graceful_on_network_error():
    """Even when openFDA is unreachable, the endpoint must return 200 with success=false, not a 500."""
    with patch("httpx.Client.get", side_effect=TimeoutException("timed out")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/signals/live-lookup",
                json={"drug_name": "ANYDRUG"},
            )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "error" in data
