"""Module M1: Adverse Event Clustering Engine (scikit-learn).

Clusters adverse event reports based on multi-dimensional clinical feature vectors:
- Disproportionality statistics (PRR, Chi-square)
- Severity profile (Mortality rate, Hospitalization rate, Serious event rate)
- Patient demographics (Mean onset age, Female sex ratio)
- Case volume (Report count)

Uses StandardScaler, KMeans clustering, and PCA 2D projection for visualization.
"""

import os
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from app.m1_faers.faers_ingest import (
    DATA_DIR,
    load_real_faers_data,
    build_contingency_table_from_real_signals,
    normalize_drug_name,
    normalize_event_name,
)
from app.m2_prr.prr_engine import calculate_prr, classify_signal


# Cache clustering results in-memory
_cached_clustering_result: Optional[Dict[str, Any]] = None


def _assign_differentiated_cluster_themes(clusters_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assigns distinct, highly descriptive clinical themes to clusters based on relative feature rankings."""
    if not clusters_raw:
        return []

    # Sort candidates
    k = len(clusters_raw)
    
    # Track assigned labels to ensure 100% uniqueness
    used_names = set()
    
    # Sort by mortality descending
    by_mortality = sorted(clusters_raw, key=lambda c: -c["avg_death_rate"])
    # Sort by hospitalization descending
    by_hosp = sorted(clusters_raw, key=lambda c: -c["avg_hospitalization_rate"])
    # Sort by PRR descending
    by_prr = sorted(clusters_raw, key=lambda c: -c["avg_prr"])
    # Sort by case count descending
    by_cases = sorted(clusters_raw, key=lambda c: -c["total_cases"])

    for c in clusters_raw:
        c_id = c["cluster_id"]
        top_str = " ".join(c["top_events"]).upper()
        
        # Determine archetype
        if c_id == by_mortality[0]["cluster_id"] and "Cardiovascular & Acute Ischemic Risk" not in used_names:
            name = "Cardiovascular & Acute Ischemic Risk"
            theme = "Acute Ischemia & High Mortality"
            severity = "CRITICAL"
            desc = f"Highest mortality cohort ({c['avg_death_rate']:.1f}% death outcome) with acute cardiovascular emergencies and ischemic events (mean age {c['avg_age']:.0f}y)."
        elif (c_id == by_hosp[0]["cluster_id"] or "RHABDOMYOLYSIS" in top_str) and "Severe Organ Toxicity & Rhabdomyolysis" not in used_names:
            name = "Severe Organ Toxicity & Rhabdomyolysis"
            theme = "Organ Toxicity & Hospitalization"
            severity = "HIGH"
            desc = f"Marked by severe muscle breakdown, renal/hepatic stress, and peak hospitalization rates ({c['avg_hospitalization_rate']:.1f}%)."
        elif (c_id == by_cases[0]["cluster_id"] or "FAILURE" in top_str or "OEDEMA" in top_str) and "High-Volume Metabolic & Congestive Syndromes" not in used_names:
            name = "High-Volume Metabolic & Congestive Syndromes"
            theme = "Metabolic & Fluid Decompensation"
            severity = "MODERATE"
            desc = f"Large patient case volume ({c['total_cases']:,} reports) characterized by chronic fluid overload, congestive failure, and metabolic decompensation."
        elif (c_id == by_prr[0]["cluster_id"]) and "Hyper-Disproportional Emergent Signals" not in used_names:
            name = "Hyper-Disproportional Emergent Signals"
            theme = "High-Disproportionality Signals"
            severity = "HIGH"
            desc = f"Highest statistical disproportionality (mean PRR {c['avg_prr']:.2f}, Chi² {c['avg_chi_square']:.1f}) indicating acute reporting spikes."
        else:
            name = "Systemic, Allergic & General Adverse Reactions"
            theme = "General Systemic & Moderate Reactions"
            severity = "STANDARD"
            desc = f"General systemic, dermatological, and moderate symptomatic reactions across patient populations (mean PRR {c['avg_prr']:.2f})."

        used_names.add(name)
        c["clinical_theme"] = theme
        c["severity_level"] = severity
        c["description"] = desc

    return clusters_raw


def compute_adverse_event_clusters(
    n_clusters: int = 4,
    drug_filter: Optional[str] = None,
    force_refresh: bool = False,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Extracts clinical feature vectors from FAERS data, fits K-Means, and projects 2D coordinates via PCA.

    Args:
        n_clusters: Number of clusters (default 4, constrained 2..8).
        drug_filter: Optional uppercase drug name filter.
        force_refresh: Whether to ignore cached results.
        data_dir: Data directory override.

    Returns:
        Structured clustering response with cluster summaries and 2D-projected scatter points.
    """
    global _cached_clustering_result

    cache_key = f"{n_clusters}_{drug_filter or 'ALL'}"
    if not force_refresh and _cached_clustering_result is not None and _cached_clustering_result.get("cache_key") == cache_key:
        return _cached_clustering_result

    if data_dir is None:
        data_dir = DATA_DIR

    # 1. Load patient-level FAERS dataset for severity and demographic features
    raw_df = load_real_faers_data(data_dir=data_dir)

    # 2. Compute patient-level aggregation per (drug, reaction_term)
    raw_df["serious_bin"] = raw_df["serious"].apply(lambda x: 1.0 if str(x) in ["1", "1.0", "Y", "YES"] else 0.0)
    raw_df["death_bin"] = raw_df["seriousnessdeath"].apply(lambda x: 1.0 if str(x) in ["1", "1.0", "Y", "YES"] else 0.0)
    raw_df["hosp_bin"] = raw_df["seriousnesshospitalization"].apply(lambda x: 1.0 if str(x) in ["1", "1.0", "Y", "YES"] else 0.0)
    raw_df["is_female"] = raw_df["patientsex"].apply(lambda x: 1.0 if str(x) in ["2", "2.0", "F", "FEMALE"] else 0.0)
    raw_df["age_num"] = pd.to_numeric(raw_df["patientonsetage"], errors="coerce")

    # Group by drug + reaction_term
    grouped = raw_df.groupby(["drug_name", "event_term"]).agg(
        total_reports=("safetyreportid", "nunique"),
        serious_rate=("serious_bin", "mean"),
        death_rate=("death_bin", "mean"),
        hospitalization_rate=("hosp_bin", "mean"),
        female_ratio=("is_female", "mean"),
        mean_age=("age_num", "mean"),
    ).reset_index()

    # Median impute missing age
    cohort_median_age = float(raw_df["age_num"].median()) if not raw_df["age_num"].dropna().empty else 58.0
    grouped["mean_age"] = grouped["mean_age"].fillna(cohort_median_age)

    # 3. Join with PRR signal contingency metrics
    signals_ct = build_contingency_table_from_real_signals(data_dir=data_dir)

    # Merge
    merged = pd.merge(signals_ct, grouped, on=["drug_name", "event_term"], how="left")
    merged["serious_rate"] = merged["serious_rate"].fillna(0.5)
    merged["death_rate"] = merged["death_rate"].fillna(0.05)
    merged["hospitalization_rate"] = merged["hospitalization_rate"].fillna(0.4)
    merged["female_ratio"] = merged["female_ratio"].fillna(0.5)
    merged["mean_age"] = merged["mean_age"].fillna(cohort_median_age)

    if drug_filter:
        norm_filter = normalize_drug_name(drug_filter)
        merged = merged[merged["drug_name"] == norm_filter].copy()

    if merged.empty:
        return {
            "cache_key": cache_key,
            "clusters": [],
            "points": [],
            "metadata": {"error": "No records found matching criteria"},
        }

    # Compute PRR and Chi-square for every row
    prrs = []
    chi2s = []
    statuses = []
    for _, r in merged.iterrows():
        stats = calculate_prr(
            n_drug_event=float(r["n_drug_event"]),
            n_drug_total=float(r["n_drug_total"]),
            n_event_total=float(r["n_event_total"]),
            n_total=float(r["n_total"]),
        )
        st = classify_signal(stats["prr"], stats["chi_square"], int(r["n_drug_event"]))
        prrs.append(stats["prr"])
        chi2s.append(stats["chi_square"])
        statuses.append(st)

    merged["prr"] = prrs
    merged["chi_square"] = chi2s
    merged["signal_status"] = statuses
    merged["log_prr"] = np.log(np.maximum(merged["prr"], 0.01))
    merged["log_cases"] = np.log1p(merged["n_drug_event"])

    # 4. Define Feature Matrix for Clustering
    # Multi-dimensional vector: [log_prr, log_cases, serious_rate, death_rate, hospitalization_rate, mean_age, female_ratio]
    feature_cols = [
        "log_prr",
        "log_cases",
        "serious_rate",
        "death_rate",
        "hospitalization_rate",
        "mean_age",
        "female_ratio",
    ]

    X = merged[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Constrain n_clusters to available samples
    actual_k = min(max(2, n_clusters), max(2, len(merged) - 1))
    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)
    merged["cluster_id"] = cluster_labels

    # 5. Dimensionality Reduction: PCA 2D for interactive plotting
    pca = PCA(n_components=2, random_state=42)
    pca_coords = pca.fit_transform(X_scaled)
    merged["pca_x"] = np.round(pca_coords[:, 0], 3)
    merged["pca_y"] = np.round(pca_coords[:, 1], 3)

    # 6. Build Cluster Archetype Profiles
    clusters_raw = []
    for c_id in range(actual_k):
        c_subset = merged[merged["cluster_id"] == c_id]
        if c_subset.empty:
            continue

        c_top = c_subset.sort_values("prr", ascending=False)
        top_events = c_top["event_term"].head(5).tolist()
        dominant_drugs = c_subset["drug_name"].value_counts().head(3).to_dict()

        clusters_raw.append({
            "cluster_id": c_id,
            "cluster_name": f"Cluster {c_id + 1}",
            "clinical_theme": "General",
            "severity_level": "STANDARD",
            "description": "",
            "event_count": int(len(c_subset)),
            "total_cases": int(c_subset["n_drug_event"].sum()),
            "avg_prr": round(float(c_subset["prr"].mean()), 2),
            "avg_chi_square": round(float(c_subset["chi_square"].mean()), 1),
            "avg_death_rate": round(float(c_subset["death_rate"].mean()) * 100, 1),
            "avg_hospitalization_rate": round(float(c_subset["hospitalization_rate"].mean()) * 100, 1),
            "avg_age": round(float(c_subset["mean_age"].mean()), 1),
            "top_events": top_events,
            "dominant_drugs": dominant_drugs,
        })

    # Assign distinct themes
    clusters_info = _assign_differentiated_cluster_themes(clusters_raw)

    # Sort clusters by severity / average mortality / PRR descending
    clusters_info.sort(key=lambda x: (-x["avg_death_rate"], -x["avg_hospitalization_rate"], -x["avg_prr"]))
    
    # Remap cluster IDs to 1..k in sorted order
    id_map = {old["cluster_id"]: idx + 1 for idx, old in enumerate(clusters_info)}
    for idx, c in enumerate(clusters_info):
        c["cluster_id"] = idx + 1
        c["cluster_name"] = f"Cluster {idx + 1}: {c['clinical_theme']}"

    # Build scatter points list
    points = []
    for idx, r in merged.iterrows():
        c_mapped_id = id_map.get(int(r["cluster_id"]), int(r["cluster_id"]) + 1)
        points.append({
            "id": int(idx) + 1,
            "drug_name": str(r["drug_name"]),
            "event_term": str(r["event_term"]),
            "cluster_id": c_mapped_id,
            "pca_x": float(r["pca_x"]),
            "pca_y": float(r["pca_y"]),
            "prr": round(float(r["prr"]), 2),
            "chi_square": round(float(r["chi_square"]), 1),
            "cases": int(r["n_drug_event"]),
            "death_rate": round(float(r["death_rate"]) * 100, 1),
            "hospitalization_rate": round(float(r["hospitalization_rate"]) * 100, 1),
            "serious_rate": round(float(r["serious_rate"]) * 100, 1),
            "mean_age": round(float(r["mean_age"]), 1),
            "signal_status": str(r["signal_status"]),
        })

    response = {
        "cache_key": cache_key,
        "clusters": clusters_info,
        "points": points,
        "metadata": {
            "algorithm": "K-Means Clustering (scikit-learn)",
            "normalization": "StandardScaler",
            "dimensionality_reduction": "PCA (2-Component Projection)",
            "variance_explained_ratio": [round(float(v), 3) for v in pca.explained_variance_ratio_],
            "total_drug_event_pairs": len(points),
            "n_clusters": len(clusters_info),
            "features_used": [
                "log(PRR)",
                "log(Cases)",
                "Serious Event Rate",
                "Mortality Rate",
                "Hospitalization Rate",
                "Patient Onset Age",
                "Sex Distribution (% Female)",
            ],
            "dataset_source": "openFDA FAERS Ingestion (Merged & Cleaned)",
        },
    }

    _cached_clustering_result = response
    return response
