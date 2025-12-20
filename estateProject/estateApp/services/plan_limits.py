import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from django.utils import timezone
from django.urls import reverse

from estateApp.models import (
    Company,
    CustomUser,
    Estate,
    PlotAllocation,
    SubscriptionPlan,
    ClientMarketerAssignment,
    MarketerAffiliation,
)


FEATURE_ESTATE_PROPERTIES = "estate_properties"
FEATURE_ALLOCATIONS = "allocations"
FEATURE_CLIENTS = "clients"
FEATURE_AFFILIATES = "affiliates"


@dataclass(frozen=True)
class PlanLimitResult:
    feature: str
    used: int
    limit: Optional[int]  # None => unlimited

    @property
    def remaining(self) -> Optional[int]:
        if self.limit is None:
            return None
        return max(int(self.limit) - int(self.used), 0)

    @property
    def is_unlimited(self) -> bool:
        return self.limit is None

    @property
    def is_exhausted(self) -> bool:
        return (self.limit is not None) and (int(self.used) >= int(self.limit))

    @property
    def usage_ratio(self) -> Optional[float]:
        if self.limit is None or self.limit <= 0:
            return None
        return float(self.used) / float(self.limit)

    @property
    def is_near_limit(self) -> bool:
        if self.limit is None or self.limit <= 0:
            return False
        ratio = self.usage_ratio or 0.0
        return ratio >= 0.8 and ratio < 1.0


def _normalize_limit(value: Any) -> Optional[int]:
    """Convert a plan feature limit into an integer or None for unlimited."""
    if value is None:
        return None

    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"", "unlimited", "infinite", "none"}:
            return None
        if v.isdigit():
            return int(v)
        try:
            return int(float(v))
        except Exception:
            return None

    if isinstance(value, (int,)):
        # 0 is treated as an actual limit (no creation allowed)
        return int(value)

    if isinstance(value, (float,)):
        return int(value)

    return None


def get_company_subscription_plan(company: Company) -> Optional[SubscriptionPlan]:
    """Resolve the company’s current SubscriptionPlan.

    Priority:
    1) Enhanced billing record: company.billing.current_plan
    2) Fallback: SubscriptionPlan(tier=company.subscription_tier)
    """
    if not company:
        return None

    billing = getattr(company, "billing", None)
    plan = getattr(billing, "current_plan", None) if billing else None
    if plan:
        return plan

    tier = getattr(company, "subscription_tier", None)
    if not tier:
        return None

    return SubscriptionPlan.objects.filter(tier=tier, is_active=True).first()


def get_plan_limits(company: Company) -> Dict[str, Optional[int]]:
    plan = get_company_subscription_plan(company)
    features = getattr(plan, "features", None) or {}

    return {
        FEATURE_ESTATE_PROPERTIES: _normalize_limit(features.get(FEATURE_ESTATE_PROPERTIES)),
        FEATURE_ALLOCATIONS: _normalize_limit(features.get(FEATURE_ALLOCATIONS)),
        FEATURE_CLIENTS: _normalize_limit(features.get(FEATURE_CLIENTS)),
        FEATURE_AFFILIATES: _normalize_limit(features.get(FEATURE_AFFILIATES)),
    }


def get_company_usage_counts(company: Company) -> Dict[str, int]:
    """Live counts for plan-limited resources.

    - estates: Estate rows for company
    - allocations: total PlotAllocation rows for company (TOTAL, not monthly)
    - clients: unique clients in company (primary + ClientMarketerAssignment)
    - affiliates: unique marketers in company (primary + MarketerAffiliation)
    """
    if not company:
        return {
            FEATURE_ESTATE_PROPERTIES: 0,
            FEATURE_ALLOCATIONS: 0,
            FEATURE_CLIENTS: 0,
            FEATURE_AFFILIATES: 0,
        }

    estates_used = Estate.objects.filter(company=company).count()
    allocations_used = PlotAllocation.objects.filter(estate__company=company).count()

    primary_client_ids = set(
        CustomUser.objects.filter(role="client", company_profile=company).values_list("id", flat=True)
    )
    affiliated_client_ids = set(
        ClientMarketerAssignment.objects.filter(company=company).values_list("client_id", flat=True).distinct()
    )
    clients_used = len(primary_client_ids | affiliated_client_ids)

    primary_marketer_ids = set(
        CustomUser.objects.filter(role="marketer", company_profile=company).values_list("id", flat=True)
    )
    affiliated_marketer_ids = set(
        MarketerAffiliation.objects.filter(company=company).values_list("marketer_id", flat=True).distinct()
    )
    affiliates_used = len(primary_marketer_ids | affiliated_marketer_ids)

    return {
        FEATURE_ESTATE_PROPERTIES: int(estates_used),
        FEATURE_ALLOCATIONS: int(allocations_used),
        FEATURE_CLIENTS: int(clients_used),
        FEATURE_AFFILIATES: int(affiliates_used),
    }


def get_limit_status(company: Company, feature: str) -> PlanLimitResult:
    limits = get_plan_limits(company)
    usage = get_company_usage_counts(company)
    return PlanLimitResult(feature=feature, used=int(usage.get(feature, 0)), limit=limits.get(feature))


def get_plan_usage_summary(company: Company) -> Dict[str, Any]:
    """Template-friendly summary."""
    plan = get_company_subscription_plan(company)
    limits = get_plan_limits(company)
    usage = get_company_usage_counts(company)

    def feature_label(feature_key: str) -> str:
        label_map = {
            FEATURE_ESTATE_PROPERTIES: "Estate properties",
            FEATURE_ALLOCATIONS: "Allocations",
            FEATURE_CLIENTS: "Clients",
            FEATURE_AFFILIATES: "Affiliates",
        }
        return label_map.get(feature_key, feature_key)

    def pack(feature_key: str) -> Dict[str, Any]:
        res = PlanLimitResult(feature=feature_key, used=int(usage.get(feature_key, 0)), limit=limits.get(feature_key))

        usage_percent: Optional[int]
        if res.limit is None or res.limit <= 0:
            usage_percent = None
        else:
            usage_percent = int(max(0, min(100, round((float(res.used) / float(res.limit)) * 100))))

        return {
            "label": feature_label(feature_key),
            "used": res.used,
            "limit": res.limit,
            "remaining": res.remaining,
            "is_unlimited": res.is_unlimited,
            "is_exhausted": res.is_exhausted,
            "is_near_limit": res.is_near_limit,
            "usage_percent": usage_percent,
        }

    packed_limits = {
        FEATURE_ESTATE_PROPERTIES: pack(FEATURE_ESTATE_PROPERTIES),
        FEATURE_ALLOCATIONS: pack(FEATURE_ALLOCATIONS),
        FEATURE_CLIENTS: pack(FEATURE_CLIENTS),
        FEATURE_AFFILIATES: pack(FEATURE_AFFILIATES),
    }

    exhausted_features = [k for k, v in packed_limits.items() if v.get("is_exhausted")]
    near_limit_features = [k for k, v in packed_limits.items() if (v.get("is_near_limit") and not v.get("is_exhausted"))]

    # Trial/subscription timing (from Company fields; billing models may also exist, but Company is the safest base).
    subscription_status = getattr(company, "subscription_status", None)
    trial_ends_at = getattr(company, "trial_ends_at", None)
    subscription_ends_at = getattr(company, "subscription_ends_at", None)
    grace_period_ends_at = getattr(company, "grace_period_ends_at", None)

    now = timezone.now()

    trial_days_remaining: Optional[int] = None
    if subscription_status == "trial" and trial_ends_at:
        try:
            trial_days_remaining = int((trial_ends_at - now).days)
        except Exception:
            trial_days_remaining = None

    subscription_days_remaining: Optional[int] = None
    if subscription_status in {"active", "expired"} and subscription_ends_at:
        try:
            subscription_days_remaining = int((subscription_ends_at - now).days)
        except Exception:
            subscription_days_remaining = None

    return {
        "plan": {
            "id": getattr(plan, "id", None),
            "tier": getattr(plan, "tier", None) or getattr(company, "subscription_tier", None),
            "name": getattr(plan, "name", None),
        },
        "subscription": {
            "status": subscription_status,
            "is_trial": subscription_status == "trial",
            "trial_ends_at": trial_ends_at,
            "trial_days_remaining": trial_days_remaining,
            "subscription_ends_at": subscription_ends_at,
            "subscription_days_remaining": subscription_days_remaining,
            "grace_period_ends_at": grace_period_ends_at,
            "is_read_only_mode": bool(getattr(company, "is_read_only_mode", False)),
        },
        "limits": packed_limits,
        "exhausted_features": exhausted_features,
        "near_limit_features": near_limit_features,
        "any_exhausted": bool(exhausted_features),
        "any_near_limit": bool(near_limit_features),
        "subscription_dashboard_url": reverse("subscription_dashboard"),
    }


def build_limit_block_message(company: Company, feature: str) -> str:
    res = get_limit_status(company, feature)

    label_map = {
        FEATURE_ESTATE_PROPERTIES: "estate properties",
        FEATURE_ALLOCATIONS: "allocations",
        FEATURE_CLIENTS: "clients",
        FEATURE_AFFILIATES: "affiliates",
    }
    label = label_map.get(feature, feature)

    if res.limit is None:
        return ""

    return (
        f"Plan limit reached: {res.used}/{res.limit} {label}. "
        f"Upgrade your subscription to add more."
    )


def can_create(company: Company, feature: str) -> Tuple[bool, PlanLimitResult]:
    res = get_limit_status(company, feature)
    return (not res.is_exhausted), res


def nearing_limit_warning(company: Company, feature: str) -> Optional[str]:
    res = get_limit_status(company, feature)
    if res.limit is None:
        return None
    if res.is_near_limit and not res.is_exhausted:
        label_map = {
            FEATURE_ESTATE_PROPERTIES: "estate properties",
            FEATURE_ALLOCATIONS: "allocations",
            FEATURE_CLIENTS: "clients",
            FEATURE_AFFILIATES: "affiliates",
        }
        label = label_map.get(feature, feature)
        threshold = int(math.ceil((res.limit or 0) * 0.8))
        return f"Approaching your {label} limit ({res.used}/{res.limit}). Consider upgrading."
    return None
