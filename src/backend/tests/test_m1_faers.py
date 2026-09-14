"""Tests for M1 FAERS Ingest Module."""

import pytest
import pandas as pd
from app.m1_faers.faers_ingest import (
    normalize_drug_name,
    normalize_event_name,
    load_demo_faers_data,
    validate_faers_records,
    build_contingency_table,
    run_m1_pipeline,
)


def test_normalize_drug_name():
    assert normalize_drug_name("  rofecoxib  ") == "ROFECOXIB"
    assert normalize_drug_name("METFORMIN") == "METFORMIN"
    assert normalize_drug_name("") == ""
    assert normalize_drug_name(None) == ""


def test_normalize_event_name():
    assert normalize_event_name("myocardial infarction") == "MYOCARDIAL INFARCTION"
    assert normalize_event_name("  NAUSEA  ") == "NAUSEA"
    assert normalize_event_name("") == ""


def test_load_demo_data():
    df = load_demo_faers_data()
    assert len(df) > 10
    assert "drug_name" in df.columns
    assert "event_term" in df.columns
    assert "report_count" in df.columns
    # All drug names normalized to uppercase
    assert all(df["drug_name"] == df["drug_name"].str.upper())
    assert all(df["report_count"] >= 0)


def test_validate_records_empty():
    df = pd.DataFrame({"drug_name": [], "event_term": [], "report_count": []})
    cleaned, issues = validate_faers_records(df)
    assert len(cleaned) == 0


def test_validate_records_removes_empty():
    df = pd.DataFrame({
        "drug_name": ["ASPIRIN", ""],
        "event_term": ["NAUSEA", "RASH"],
        "report_count": [10, 5],
    })
    cleaned, issues = validate_faers_records(df)
    assert len(cleaned) == 1
    assert len(issues) > 0


def test_build_contingency_table():
    df = pd.DataFrame({
        "drug_name": ["ASPIRIN", "ASPIRIN", "WARFARIN"],
        "event_term": ["NAUSEA", "RASH", "NAUSEA"],
        "report_count": [100, 50, 200],
    })
    ct = build_contingency_table(df)
    assert "n_drug_event" in ct.columns
    assert "n_drug_total" in ct.columns
    assert "n_event_total" in ct.columns
    assert "n_total" in ct.columns
    assert ct["n_total"].iloc[0] == 350


def test_build_contingency_table_empty():
    df = pd.DataFrame({"drug_name": [], "event_term": [], "report_count": []})
    ct = build_contingency_table(df)
    assert ct.empty


def test_run_m1_pipeline():
    result = run_m1_pipeline()
    assert "contingency_table" in result
    assert "total_records" in result
    assert "drugs" in result
    assert "events" in result
    assert "issues" in result
    assert result["total_records"] > 0
    assert len(result["drugs"]) > 0
    assert len(result["events"]) > 0
    # Rofecoxib should be in dataset
    assert "ROFECOXIB" in result["drugs"]
