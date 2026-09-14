"""Tests for IBM Bob Copilot, Custom PRR calculation, and M4 Presets API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_copilot_suggestions_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/copilot/suggestions")
    assert response.status_code == 200
    suggestions = response.json()
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    assert any("Vioxx" in s for s in suggestions)


@pytest.mark.asyncio
async def test_copilot_query_vioxx():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/copilot/query",
            json={"query": "Why was Vioxx flagged for myocardial infarction?"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "Vioxx" in data["answer"] or "Rofecoxib" in data["answer"]
    assert "242" in data["answer"] or "withdrawal" in data["answer"].lower()
    assert len(data["suggested_followups"]) > 0


@pytest.mark.asyncio
async def test_copilot_query_prr_methodology():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/copilot/query",
            json={"query": "How is the Proportional Reporting Ratio (PRR) calculated?"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "PRR" in data["answer"] or "Evans" in data["answer"]


@pytest.mark.asyncio
async def test_copilot_query_ctd_module3():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/copilot/query",
            json={"query": "What are the requirements for ICH M4 Module 3 Quality CMC?"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "Module 3" in data["answer"] or "Quality" in data["answer"]


@pytest.mark.asyncio
async def test_custom_prr_calculation_cells():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/signals/calculate",
            json={
                "drug_name": "TEST-DRUG",
                "event_term": "ARRHYTHMIA",
                "a": 50,
                "b": 200,
                "c": 100,
                "d": 5000,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["drug_name"] == "TEST-DRUG"
    assert data["event_term"] == "ARRHYTHMIA"
    assert data["n_drug_event"] == 50
    assert data["n_drug_total"] == 250
    assert data["metrics"]["prr"] > 2.0
    assert data["signal_status"] == "SIGNAL"
    assert data["is_signal"] is True
    assert "explanation" in data


@pytest.mark.asyncio
async def test_custom_prr_calculation_margins():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/signals/calculate",
            json={
                "drug_name": "ROFECOXIB",
                "event_term": "MYOCARDIAL INFARCTION",
                "n_drug_event": 17938,
                "n_drug_total": 44279,
                "n_event_total": 173520,
                "n_total": 20692690,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert abs(data["metrics"]["prr"] - 53.77) < 0.05
    assert data["signal_status"] == "SIGNAL"


@pytest.mark.asyncio
async def test_custom_prr_invalid_input():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/signals/calculate",
            json={"drug_name": "INVALID"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_m4_presets_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/m4/presets")
    assert response.status_code == 200
    presets = response.json()
    assert "VIOXX_NDA_21042" in presets
    assert "BOB701_ONCOLOGY" in presets


@pytest.mark.asyncio
async def test_m4_single_preset_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/m4/presets/VIOXX_NDA_21042")
    assert response.status_code == 200
    preset = response.json()
    assert preset["drug_name"] == "VIOXX"
    assert len(preset["sections"]) > 0
