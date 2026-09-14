"""Pre-packaged candidate dossiers for one-click auditing and testing."""

PRESET_DOSSIERS = {
    "VIOXX_NDA_21042": {
        "submission_title": "Vioxx (Rofecoxib) NDA 21-042 Safety Audit",
        "drug_name": "VIOXX",
        "target_region": "FDA / US",
        "sections": [
            {
                "section_id": "1.1",
                "title": "Forms and Administrative Information",
                "description": "FDA Form 356h, application for approval to market rofecoxib.",
            },
            {
                "section_id": "2.3",
                "title": "Quality Overall Summary",
                "description": "CMC chemistry, manufacturing, and control summaries.",
            },
            {
                "section_id": "2.5",
                "title": "Clinical Overview",
                "description": "Benefits and risks assessment focusing on upper GI tolerability vs non-selective NSAIDs; pre-market pooled cardiovascular RR = 1.12.",
            },
            {
                "section_id": "3.2.S.1",
                "title": "General Information on Drug Substance",
                "description": "Nomenclature, structure, and physicochemical properties of rofecoxib.",
            },
            {
                "section_id": "4.2.3",
                "title": "Toxicology Study Reports",
                "description": "Repeat-dose GLP oral toxicity studies in rats and primates.",
            },
            {
                "section_id": "5.3.5",
                "title": "Reports of Efficacy and Safety Studies",
                "description": "Pivotal Phase 3 osteoarthritis and acute pain clinical study reports.",
            },
        ],
    },
    "BOB701_ONCOLOGY": {
        "submission_title": "BOB-701 Investigational Solid Tumor Oncology Candidate NDA",
        "drug_name": "BOB-701",
        "target_region": "FDA / EMA",
        "sections": [
            {
                "section_id": "1.1",
                "title": "Forms and Administrative Information",
                "description": "FDA Form 356h and administrative cover letter.",
            },
            {
                "section_id": "1.3",
                "title": "Product Information / Prescribing Information",
                "description": "Draft package insert and structured product labeling.",
            },
            {
                "section_id": "2.3",
                "title": "Quality Overall Summary",
                "description": "Quality overall summary covering critical quality attributes.",
            },
            {
                "section_id": "2.4",
                "title": "Nonclinical Overview",
                "description": "Assessment of pharmacological target selectivity and in vitro hERG assay.",
            },
            {
                "section_id": "2.5",
                "title": "Clinical Overview",
                "description": "Evaluation of progression-free survival and overall response rate.",
            },
            {
                "section_id": "3.2.P.2",
                "title": "Pharmaceutical Development",
                "description": "Formulation development and sterilization validation.",
            },
            {
                "section_id": "4.2.1",
                "title": "Pharmacology Primary Pharmacodynamics",
                "description": "Target kinase inhibition profiling and xenograft tumor regression.",
            },
            {
                "section_id": "5.3.1",
                "title": "Reports of Biopharmaceutic Studies",
                "description": "Absolute oral bioavailability and food effect studies.",
            },
            {
                "section_id": "5.3.5",
                "title": "Reports of Efficacy and Safety Studies",
                "description": "Multicenter Phase 2/3 randomized controlled study reports.",
            },
        ],
    },
    "MINIMAL_EARLY_IND": {
        "submission_title": "Phase 1 Exploratory IND Application",
        "drug_name": "EXP-101",
        "target_region": "FDA / US",
        "sections": [
            {
                "section_id": "1.1",
                "title": "Forms and Administrative Information",
                "description": "Form FDA 1571 and investigator curriculum vitae.",
            },
            {
                "section_id": "4.2.1",
                "title": "Pharmacology Primary Studies",
                "description": "In vitro target engagement and binding kinetics.",
            },
            {
                "section_id": "4.2.3",
                "title": "Toxicology Studies",
                "description": "14-day rodent acute tolerability studies.",
            },
        ],
    },
}
