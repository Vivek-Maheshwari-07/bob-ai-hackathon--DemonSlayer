"""Tests for M4 FastAPI Endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_all_requirements_endpoint():
    response = client.get("/api/v1/m4/requirements")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 30


def test_get_module_requirements_endpoint():
    # Test valid module
    response = client.get("/api/v1/m4/module/2")
    assert response.status_code == 200
    data = response.json()
    assert all(item["module_id"] == 2 for item in data)

    # Test invalid module
    response_invalid = client.get("/api/v1/m4/module/9")
    assert response_invalid.status_code == 400


def test_evaluate_dossier_endpoint():
    payload = {
        "submission_title": "FastAPI Candidate Dossier",
        "drug_name": "BOB-99",
        "target_region": "Global",
        "sections": [
            {
                "section_id": "2.5",
                "title": "Clinical Overview",
                "description": "Comprehensive review of safety and efficacy",
            },
            {
                "section_id": "3.2.S.1",
                "title": "General Information",
                "description": "Nomenclature and physical structure",
            },
        ],
    }
    response = client.post("/api/v1/m4/check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["submission_title"] == "FastAPI Candidate Dossier"
    assert "overall_completeness" in data
    assert "modules" in data
    assert "module_1" in data["modules"]
    assert "module_2" in data["modules"]
    assert len(data["present_sections"]) >= 2


def test_quick_check_text_endpoint():
    raw_text = (
        "1.1 Forms and Administrative Information\n"
        "2.5 Clinical Overview - Benefit-risk balance\n"
        "3.2.S.4 Control of Drug Substance - Release specifications\n"
    )
    response = client.post(
        "/api/v1/m4/quick-check-text",
        content=raw_text,
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["present_total"] >= 3


def test_check_pdf_endpoint():
    # Synthetic PDF text stream
    fake_pdf_bytes = b"%PDF-1.4\n%Fake PDF content for test\n"
    response = client.post(
        "/api/v1/m4/check-pdf",
        files={"file": ("dossier.pdf", fake_pdf_bytes, "application/pdf")},
        data={"submission_title": "Uploaded PDF Test", "enable_reasoning": "false"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["submission_title"] == "Uploaded PDF Test"
    assert "overall_completeness" in data
