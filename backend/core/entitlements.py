"""v1 feature codes (PLT-2), grouped by subscription tier (docs/00 §2)."""

CORE_FEATURES = ["reception", "appointments", "billing", "emr", "reports"]
PLUS_FEATURES = ["nphies", "zatca_phase2", "lab", "pharmacy"]
PRO_FEATURES = ["radiology", "rsd", "multi_branch", "api_access"]

ALL_V1_FEATURES = CORE_FEATURES + PLUS_FEATURES + PRO_FEATURES
