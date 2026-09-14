"""Tests for M1 FAERS Ingest Module (Real OpenFDA Data)."""

import pytest
import pandas as pd
from app.m1_faers.faers_ingest import (
    normalize_drug_name,
    normalize_event_name,
    load_real_faers_data,
    validate_faers_records,
    build_contingency_table,
    build_contingency_table_from_real_signals,
    run_m1_pipeline,
)


def test_normalize_drug_name():
    assert normalize_drug_name("  vioxx  ") == "VIOXX"
    assert normalize_drug_name("BAYCOL") == "BAYCOL"
    assert normalize_drug_name("AVANDIA") == "AVANDIA"
    assert normalize_drug_name("") == ""
    assert normalize_drug_name(None) == ""


def test_normalize_event_name():
    assert normalize_event_name("myocardial infarction") == "MYOCARDIAL INFARCTION"
    assert normalize_event_name("  RHABDOMYOLYSIS  ") == "RHABDOMYOLYSIS"
    assert normalize_event_name("") == ""
    assert normalize_event_name(None) == ""


def test_load_real_faers_data():
    df = load_real_faers_data()
    assert len(df) > 1000
    assert "drug" in df.columns
    assert "reaction_term" in df.columns
    assert "drug_name" in df.columns
    assert "event_term" in df.columns
    # Drug names normalized to uppercase
    assert all(df["drug_name"] == df["drug_name"].str.upper())
    # Drugs present should match the real openFDA dataset
    drugs = set(df["drug_name"].unique())
    assert {"VIOXX", "BAYCOL", "AVANDIA"}.issubset(drugs)


def test_validate_records_empty():
    df = pd.DataFrame({"drug_name": [], "event_term": [], "report_count": []})
    cleaned, issues = validate_faers_records(df)
    assert len(cleaned) == 0


def test_validate_records_removes_empty():
    df = pd.DataFrame({
        "drug_name": ["VIOXX", ""],
        "event_term": ["MYOCARDIAL INFARCTION", "NAUSEA"],
        "report_count": [10, 5],
    })
    cleaned, issues = validate_faers_records(df)
    assert len(cleaned) == 1
    assert len(issues) > 0


def test_build_contingency_table():
    df = pd.DataFrame({
        "drug_name": ["VIOXX", "VIOXX", "BAYCOL"],
        "event_term": ["MYOCARDIAL INFARCTION", "RASH", "MYOCARDIAL INFARCTION"],
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
    # Real drug names from openFDA dataset
    assert sorted(result["drugs"]) == ["AVANDIA", "BAYCOL", "VIOXX"]
    assert "VIOXX" in result["drugs"]
    assert "BAYCOL" in result["drugs"]
    assert "AVANDIA" in result["drugs"]
    assert any("openFDA" in issue for issue in result["issues"])


def test_real_contingency_table_values():
    result = run_m1_pipeline()
    ct = result["contingency_table"]
    row = ct[(ct["drug_name"] == "VIOXX") & (ct["event_term"] == "MYOCARDIAL INFARCTION")]
    assert not row.empty
    rec = row.iloc[0]
    assert int(rec["n_drug_event"]) == 17938
    assert int(rec["n_drug_total"]) == 44279
    assert int(rec["n_total"]) == 20692690
