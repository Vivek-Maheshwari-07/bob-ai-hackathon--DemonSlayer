"""Module M1: FAERS Ingest, Clean & Normalize.

Loads, validates, cleans, and normalizes FDA FAERS adverse event data.
Produces drug-event contingency tables consumed by M2 PRR Signal Engine.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


# ─── Curated realistic FAERS-style demo dataset ────────────────────────────
# Based on publicly known pharmacovigilance signals for educational demonstration.
# Sources: FDA FAERS public dashboard data, published pharmacoepidemiology literature.
DEMO_FAERS_RECORDS = [
    # Drug, Adverse Event, Report Count
    # Rofecoxib (Vioxx) - classic historical signal
    ("ROFECOXIB", "MYOCARDIAL INFARCTION", 847),
    ("ROFECOXIB", "STROKE", 312),
    ("ROFECOXIB", "CARDIAC FAILURE", 203),
    ("ROFECOXIB", "THROMBOSIS", 156),
    ("ROFECOXIB", "PULMONARY EMBOLISM", 89),
    ("ROFECOXIB", "NAUSEA", 1102),
    ("ROFECOXIB", "ABDOMINAL PAIN", 743),
    # Metformin - reference drug (well-known safety)
    ("METFORMIN", "LACTIC ACIDOSIS", 24),
    ("METFORMIN", "NAUSEA", 2341),
    ("METFORMIN", "DIARRHOEA", 1876),
    ("METFORMIN", "VITAMIN B12 DEFICIENCY", 312),
    ("METFORMIN", "RENAL IMPAIRMENT", 67),
    # Simvastatin - statin signal
    ("SIMVASTATIN", "RHABDOMYOLYSIS", 134),
    ("SIMVASTATIN", "MYOPATHY", 289),
    ("SIMVASTATIN", "HEPATOTOXICITY", 78),
    ("SIMVASTATIN", "NAUSEA", 456),
    ("SIMVASTATIN", "MUSCLE WEAKNESS", 412),
    # Clopidogrel
    ("CLOPIDOGREL", "GASTROINTESTINAL HAEMORRHAGE", 341),
    ("CLOPIDOGREL", "THROMBOCYTOPENIA", 156),
    ("CLOPIDOGREL", "THROMBOTIC THROMBOCYTOPENIC PURPURA", 89),
    ("CLOPIDOGREL", "NAUSEA", 312),
    ("CLOPIDOGREL", "RASH", 201),
    # Fluoroquinolone antibiotics
    ("CIPROFLOXACIN", "TENDON RUPTURE", 201),
    ("CIPROFLOXACIN", "QT PROLONGATION", 178),
    ("CIPROFLOXACIN", "PERIPHERAL NEUROPATHY", 134),
    ("CIPROFLOXACIN", "NAUSEA", 923),
    ("CIPROFLOXACIN", "DIARRHOEA", 712),
    # Warfarin
    ("WARFARIN", "HAEMORRHAGE", 1234),
    ("WARFARIN", "INTRACRANIAL HAEMORRHAGE", 312),
    ("WARFARIN", "GASTROINTESTINAL HAEMORRHAGE", 456),
    ("WARFARIN", "SKIN NECROSIS", 34),
    ("WARFARIN", "NAUSEA", 234),
    # Ibuprofen
    ("IBUPROFEN", "GASTROINTESTINAL HAEMORRHAGE", 623),
    ("IBUPROFEN", "RENAL IMPAIRMENT", 201),
    ("IBUPROFEN", "CARDIAC FAILURE", 134),
    ("IBUPROFEN", "NAUSEA", 1456),
    ("IBUPROFEN", "DYSPEPSIA", 2103),
    # Amiodarone
    ("AMIODARONE", "PULMONARY TOXICITY", 312),
    ("AMIODARONE", "THYROID DISORDERS", 445),
    ("AMIODARONE", "HEPATOTOXICITY", 178),
    ("AMIODARONE", "QT PROLONGATION", 234),
    ("AMIODARONE", "PHOTOSENSITIVITY", 156),
    # Lithium
    ("LITHIUM", "RENAL IMPAIRMENT", 289),
    ("LITHIUM", "TREMOR", 567),
    ("LITHIUM", "HYPOTHYROIDISM", 312),
    ("LITHIUM", "NAUSEA", 423),
    ("LITHIUM", "TOXICITY", 134),
]


def normalize_drug_name(name: str) -> str:
    """Normalizes drug name to uppercase with controlled whitespace."""
    if not name or not isinstance(name, str):
        return ""
    return re.sub(r"\s+", " ", name.strip().upper())


def normalize_event_name(name: str) -> str:
    """Normalizes adverse event term using MedDRA-style capitalization."""
    if not name or not isinstance(name, str):
        return ""
    return re.sub(r"\s+", " ", name.strip().upper())


def load_demo_faers_data() -> pd.DataFrame:
    """Loads and returns the curated FAERS demo dataset as a DataFrame.

    Returns:
        DataFrame with columns: drug_name, event_term, report_count
    """
    records = []
    for drug, event, count in DEMO_FAERS_RECORDS:
        records.append({
            "drug_name": normalize_drug_name(drug),
            "event_term": normalize_event_name(event),
            "report_count": max(0, int(count)),
        })
    return pd.DataFrame(records)


def load_faers_from_csv(filepath: str) -> Optional[pd.DataFrame]:
    """Attempts to load raw FAERS data from a CSV export.

    Args:
        filepath: Path to FAERS DRUG/REAC export CSV.

    Returns:
        Normalized DataFrame or None if loading fails.
    """
    try:
        df = pd.read_csv(filepath, dtype=str, low_memory=False)
        # Typical FAERS DRUG.csv columns: primaryid, caseid, drug_seq, drugname, ...
        # Typical FAERS REAC.csv: primaryid, caseid, pt (Preferred Term)
        if "drugname" in df.columns:
            df["drug_name"] = df["drugname"].apply(normalize_drug_name)
        elif "DRUGNAME" in df.columns:
            df["drug_name"] = df["DRUGNAME"].apply(normalize_drug_name)
        else:
            return None
        if "pt" in df.columns:
            df["event_term"] = df["pt"].apply(normalize_event_name)
        elif "PT" in df.columns:
            df["event_term"] = df["PT"].apply(normalize_event_name)
        else:
            return None
        df["report_count"] = 1
        return df[["drug_name", "event_term", "report_count"]].dropna()
    except Exception:
        return None


def validate_faers_records(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Validates FAERS records and returns cleaned data with validation messages.

    Args:
        df: Raw FAERS DataFrame.

    Returns:
        Tuple of (cleaned_df, list_of_issues)
    """
    issues = []
    original_count = len(df)

    # Guard: empty DataFrame
    if df.empty:
        return df, issues

    # Ensure string dtype before using .str accessor
    df = df.copy()
    df["drug_name"] = df["drug_name"].astype(str).fillna("")
    df["event_term"] = df["event_term"].astype(str).fillna("")

    # Drop rows with empty drug or event
    df = df[df["drug_name"].str.len() > 0].copy()
    df = df[df["event_term"].str.len() > 0].copy()
    dropped = original_count - len(df)
    if dropped > 0:
        issues.append(f"Dropped {dropped} records with empty drug or event fields.")

    # Ensure report_count is numeric and positive
    df["report_count"] = pd.to_numeric(df["report_count"], errors="coerce").fillna(0)
    neg_count = (df["report_count"] < 0).sum()
    if neg_count > 0:
        issues.append(f"Clamped {neg_count} negative report_count values to 0.")
        df["report_count"] = df["report_count"].clip(lower=0)

    return df, issues



def build_contingency_table(df: pd.DataFrame) -> pd.DataFrame:
    """Builds drug-event contingency table from FAERS records.

    Aggregates report counts per drug-event pair. Required by M2 PRR engine.
    Contingency table structure follows FDA pharmacovigilance methodology.

    Args:
        df: Normalized FAERS DataFrame.

    Returns:
        Contingency table DataFrame:
            drug_name | event_term | n_drug_event | n_drug_total | n_event_total | n_total
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "drug_name", "event_term", "n_drug_event",
            "n_drug_total", "n_event_total", "n_total"
        ])

    # n_drug_event: reports for this drug+event pair
    grp = df.groupby(["drug_name", "event_term"])["report_count"].sum().reset_index()
    grp.rename(columns={"report_count": "n_drug_event"}, inplace=True)

    # n_drug_total: all reports mentioning this drug
    drug_totals = df.groupby("drug_name")["report_count"].sum().reset_index()
    drug_totals.rename(columns={"report_count": "n_drug_total"}, inplace=True)

    # n_event_total: all reports mentioning this event (across all drugs)
    event_totals = df.groupby("event_term")["report_count"].sum().reset_index()
    event_totals.rename(columns={"report_count": "n_event_total"}, inplace=True)

    # n_total: total reports
    n_total = int(df["report_count"].sum())

    ct = grp.merge(drug_totals, on="drug_name", how="left")
    ct = ct.merge(event_totals, on="event_term", how="left")
    ct["n_total"] = n_total

    return ct.sort_values(["drug_name", "event_term"]).reset_index(drop=True)


def run_m1_pipeline(source: Optional[str] = None) -> Dict[str, Any]:
    """Runs complete M1 FAERS ingest, clean, and normalize pipeline.

    Args:
        source: Optional path to raw FAERS CSV file. Uses demo data if None/invalid.

    Returns:
        Dictionary with:
            - contingency_table: pd.DataFrame ready for M2 PRR engine
            - total_records: int
            - drugs: list of unique drug names
            - events: list of unique adverse event terms
            - issues: list of validation messages
    """
    issues: List[str] = []

    # Load data
    if source:
        raw_df = load_faers_from_csv(source)
        if raw_df is None:
            issues.append(f"Could not load FAERS data from '{source}'. Falling back to demo dataset.")
            raw_df = load_demo_faers_data()
    else:
        issues.append("No FAERS source specified. Using curated demo dataset.")
        raw_df = load_demo_faers_data()

    # Validate
    clean_df, val_issues = validate_faers_records(raw_df)
    issues.extend(val_issues)

    # Build contingency table
    ct = build_contingency_table(clean_df)

    return {
        "contingency_table": ct,
        "total_records": int(clean_df["report_count"].sum()),
        "drugs": sorted(ct["drug_name"].unique().tolist()),
        "events": sorted(ct["event_term"].unique().tolist()),
        "issues": issues,
    }
