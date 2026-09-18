"""Module M1: FAERS Ingest, Clean & Normalize (Real OpenFDA Pipeline).

Loads, validates, cleans, and normalizes FDA FAERS adverse event data.
Produces drug-event contingency tables consumed by M2 PRR Signal Engine,
sourced from verified openFDA FAERS data artifacts.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


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


def load_real_faers_data(data_dir: Optional[str] = None) -> pd.DataFrame:
    """Loads and returns the real openFDA FAERS dataset from merged_clean.csv.

    Args:
        data_dir: Optional directory containing merged_clean.csv.

    Returns:
        DataFrame with uppercase drug and reaction_term names.
    """
    if data_dir is None:
        data_dir = DATA_DIR
    filepath = os.path.join(data_dir, "merged_clean.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Real FAERS data file not found: {filepath}")

    df = pd.read_csv(filepath, low_memory=False)
    if "drug" in df.columns:
        df["drug"] = df["drug"].astype(str).apply(normalize_drug_name)
        df["drug_name"] = df["drug"]
    if "reaction_term" in df.columns:
        df["reaction_term"] = df["reaction_term"].astype(str).apply(normalize_event_name)
        df["event_term"] = df["reaction_term"]
    return df


def build_contingency_table_from_real_signals(data_dir: Optional[str] = None) -> pd.DataFrame:
    """Reads real M2 signal CSV files and constructs the standardized contingency table.

    Reads data/m2_signals/*_signals.csv (excluding all_signals_ranked.csv),
    renames reaction_term -> event_term, drug -> drug_name, a -> n_drug_event,
    and derives n_drug_total = a + b, n_event_total = a + c, n_total = a + b + c + d
    from the real contingency cells computed upstream against openFDA background.

    Args:
        data_dir: Optional data directory containing m2_signals/.

    Returns:
        Standardized contingency table DataFrame.
    """
    if data_dir is None:
        data_dir = DATA_DIR
    signals_dir = os.path.join(data_dir, "m2_signals")
    if not os.path.isdir(signals_dir):
        raise FileNotFoundError(f"Signals directory not found: {signals_dir}")

    dfs = []
    for fname in sorted(os.listdir(signals_dir)):
        if fname.endswith("_signals.csv") and fname != "all_signals_ranked.csv":
            path = os.path.join(signals_dir, fname)
            sub_df = pd.read_csv(path)
            dfs.append(sub_df)

    if not dfs:
        raise FileNotFoundError(f"No *_signals.csv found in {signals_dir}")

    df = pd.concat(dfs, ignore_index=True)
    df.rename(
        columns={
            "drug": "drug_name",
            "reaction_term": "event_term",
            "a": "n_drug_event",
        },
        inplace=True,
    )
    df["drug_name"] = df["drug_name"].apply(normalize_drug_name)
    df["event_term"] = df["event_term"].apply(normalize_event_name)

    # Derive standard contingency totals
    df["n_drug_total"] = df["n_drug_event"] + df["b"]
    df["n_event_total"] = df["n_drug_event"] + df["c"]
    df["n_total"] = df["n_drug_event"] + df["b"] + df["c"] + df["d"]

    # Reorder columns
    cols = [
        "drug_name",
        "event_term",
        "n_drug_event",
        "n_drug_total",
        "n_event_total",
        "n_total",
        "b",
        "c",
        "d",
    ]
    other_cols = [c for c in df.columns if c not in cols]
    return df[cols + other_cols].sort_values(["drug_name", "event_term"]).reset_index(drop=True)


def load_faers_from_csv(filepath: str) -> Optional[pd.DataFrame]:
    """Attempts to load raw FAERS data from a CSV export.

    Args:
        filepath: Path to FAERS DRUG/REAC export CSV.

    Returns:
        Normalized DataFrame or None if loading fails.
    """
    try:
        df = pd.read_csv(filepath, dtype=str, low_memory=False)
        if "drugname" in df.columns:
            df["drug_name"] = df["drugname"].apply(normalize_drug_name)
        elif "DRUGNAME" in df.columns:
            df["drug_name"] = df["DRUGNAME"].apply(normalize_drug_name)
        elif "drug" in df.columns:
            df["drug_name"] = df["drug"].apply(normalize_drug_name)
        else:
            return None

        if "pt" in df.columns:
            df["event_term"] = df["pt"].apply(normalize_event_name)
        elif "PT" in df.columns:
            df["event_term"] = df["PT"].apply(normalize_event_name)
        elif "reaction_term" in df.columns:
            df["event_term"] = df["reaction_term"].apply(normalize_event_name)
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
    if "report_count" in df.columns:
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

    count_col = "report_count" if "report_count" in df.columns else None
    if count_col is None:
        df = df.copy()
        df["report_count"] = 1
        count_col = "report_count"

    # n_drug_event: reports for this drug+event pair
    grp = df.groupby(["drug_name", "event_term"])[count_col].sum().reset_index()
    grp.rename(columns={count_col: "n_drug_event"}, inplace=True)

    # n_drug_total: all reports mentioning this drug
    drug_totals = df.groupby("drug_name")[count_col].sum().reset_index()
    drug_totals.rename(columns={count_col: "n_drug_total"}, inplace=True)

    # n_event_total: all reports mentioning this event (across all drugs)
    event_totals = df.groupby("event_term")[count_col].sum().reset_index()
    event_totals.rename(columns={count_col: "n_event_total"}, inplace=True)

    # n_total: total reports
    n_total = int(df[count_col].sum())

    ct = grp.merge(drug_totals, on="drug_name", how="left")
    ct = ct.merge(event_totals, on="event_term", how="left")
    ct["n_total"] = n_total

    return ct.sort_values(["drug_name", "event_term"]).reset_index(drop=True)


def run_m1_pipeline(source: Optional[str] = None, data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Runs complete M1 FAERS ingest, clean, and normalize pipeline.

    Loads real openFDA FAERS data artifacts or an optional external source.

    Args:
        source: Optional path to raw FAERS CSV file.
        data_dir: Optional path to directory with data/ artifacts.

    Returns:
        Dictionary with:
            - contingency_table: pd.DataFrame ready for M2 PRR engine
            - total_records: int
            - drugs: list of unique drug names
            - events: list of unique adverse event terms
            - issues: list of validation messages
    """
    issues: List[str] = []

    if source:
        raw_df = load_faers_from_csv(source)
        if raw_df is not None:
            clean_df, val_issues = validate_faers_records(raw_df)
            issues.extend(val_issues)
            ct = build_contingency_table(clean_df)
            total_records = int(clean_df["report_count"].sum())
        else:
            issues.append(f"Could not load custom CSV from '{source}'. Sourcing real openFDA dataset.")
            ct = build_contingency_table_from_real_signals(data_dir=data_dir)
            try:
                clean_df = load_real_faers_data(data_dir=data_dir)
                total_records = len(clean_df)
            except Exception:
                total_records = int(ct["n_drug_event"].sum())
            issues.append("Data loaded from real openFDA FAERS pipeline artifacts (VIOXX, BAYCOL, AVANDIA).")
    else:
        ct = build_contingency_table_from_real_signals(data_dir=data_dir)
        try:
            clean_df = load_real_faers_data(data_dir=data_dir)
            total_records = len(clean_df)
        except Exception:
            total_records = int(ct["n_drug_event"].sum())
        issues.append("Data loaded from real openFDA FAERS pipeline artifacts (VIOXX, BAYCOL, AVANDIA).")

    return {
        "contingency_table": ct,
        "total_records": total_records,
        "drugs": sorted(ct["drug_name"].unique().tolist()),
        "events": sorted(ct["event_term"].unique().tolist()),
        "issues": issues,
    }
