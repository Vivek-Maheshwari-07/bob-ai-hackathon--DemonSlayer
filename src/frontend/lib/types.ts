// Domain Type Definitions for Safety & CTD Readiness Checker

export interface ClusterProfile {
  cluster_id: number;
  cluster_name: string;
  clinical_theme: string;
  severity_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'STANDARD';
  description: string;
  event_count: number;
  total_cases: number;
  avg_prr: number;
  avg_chi_square: number;
  avg_death_rate: number;
  avg_hospitalization_rate: number;
  avg_age: number;
  top_events: string[];
  dominant_drugs: Record<string, number>;
}

export interface ClusterPoint {
  id: number;
  drug_name: string;
  event_term: string;
  cluster_id: number;
  pca_x: number;
  pca_y: number;
  prr: number;
  chi_square: number;
  cases: number;
  death_rate: number;
  hospitalization_rate: number;
  serious_rate: number;
  mean_age: number;
  signal_status: string;
  is_imputed?: boolean;
}

export interface ClusteringResponse {
  cache_key?: string;
  clusters: ClusterProfile[];
  points: ClusterPoint[];
  metadata: {
    algorithm: string;
    normalization: string;
    dimensionality_reduction: string;
    variance_explained_ratio?: number[];
    silhouette_score?: number | null;
    total_drug_event_pairs: number;
    n_clusters: number;
    imputed_pairs_count?: number;
    imputed_pairs_pct?: number;
    features_used: string[];
    dataset_source: string;
  };
}

