"""RBAC registry: permission codes and seeded role templates (PLT-4).

Permissions are `module.action` strings. This registry is the single source of
truth — roles store validated subsets, and the registry grows with each
milestone. Role templates mirror the actor list in docs/01 §1; tenants clone
and customize them (Clinic Admin UI in a later milestone).
"""

PERMISSIONS: dict[str, list[str]] = {
    "reception": [
        "view",
        "register_patient",
        "manage_appointments",
        "create_visit",
        "check_eligibility",
    ],
    "billing": ["view", "invoice", "take_payment", "refund", "day_end_close"],
    "claims": ["view", "request_approval", "submit", "reconcile", "work_rejections"],
    "emr": ["view", "record_vitals", "consult", "order", "prescribe", "sign"],
    "lab": ["view", "collect_sample", "enter_results", "validate"],
    "radiology": ["view", "perform_study", "report", "sign"],
    "pharmacy": ["view", "dispense", "pos", "manage_stock", "purchase", "rsd"],
    "inventory": ["view", "purchase", "receive", "count"],
    "reports": ["view", "export"],
    "admin": [
        "manage_users",
        "manage_roles",
        "manage_catalog",
        "manage_price_lists",
        "manage_templates",
        "manage_branches",
        "view_audit",
    ],
}

ALL_PERMISSION_CODES = frozenset(
    f"{module}.{action}" for module, actions in PERMISSIONS.items() for action in actions
)

_ALL_VIEW_CODES = [f"{module}.view" for module in PERMISSIONS if "view" in PERMISSIONS[module]]


def _codes(*specs: str) -> list[str]:
    """Expand `module.*` against the registry; reject codes it doesn't know."""
    expanded: list[str] = []
    for spec in specs:
        module, _, action = spec.partition(".")
        if action == "*":
            expanded.extend(f"{module}.{a}" for a in PERMISSIONS[module])
        elif spec in ALL_PERMISSION_CODES:
            expanded.append(spec)
        else:
            raise ValueError(f"Unknown permission code: {spec}")
    return expanded


# (name_en, name_ar, permission codes) — one template per tenant role in docs/01 §1.
# Platform Admin is the vendor (tenant IS NULL) and is not a tenant role.
ROLE_TEMPLATES: list[tuple[str, str, list[str]]] = [
    (
        "Receptionist",
        "موظف الاستقبال",
        _codes("reception.*", "billing.view", "billing.invoice", "billing.take_payment"),
    ),
    ("Cashier", "أمين الصندوق", _codes("billing.*", "reception.view", "reports.view")),
    (
        "Insurance Coordinator",
        "منسق التأمين",
        _codes("claims.*", "reception.view", "billing.view"),
    ),
    (
        "Nurse",
        "ممرض",
        _codes("reception.view", "emr.view", "emr.record_vitals", "lab.collect_sample"),
    ),
    (
        "Doctor",
        "طبيب",
        _codes("emr.*", "reception.view", "lab.view", "radiology.view", "pharmacy.view"),
    ),
    ("Lab Technician", "فني مختبر", _codes("lab.view", "lab.collect_sample", "lab.enter_results")),
    ("Lab Supervisor", "مشرف مختبر", _codes("lab.*", "reports.view")),
    ("Radiology Technician", "فني أشعة", _codes("radiology.view", "radiology.perform_study")),
    ("Radiologist", "طبيب أشعة", _codes("radiology.*", "reports.view")),
    ("Pharmacist", "صيدلي", _codes("pharmacy.*", "inventory.view")),
    ("Inventory Officer", "مسؤول المخزون", _codes("inventory.*", "pharmacy.view")),
    ("Clinic Admin", "مدير العيادة", _codes("admin.*", "reports.*", *_ALL_VIEW_CODES)),
    ("Owner", "المالك", _codes("reports.*", *_ALL_VIEW_CODES)),
]
