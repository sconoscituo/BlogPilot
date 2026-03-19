"""구독 플랜 관리 서비스"""
from enum import Enum

class PlanType(str, Enum):
    FREE = "free"
    BASIC = "basic"       # 월 9,900원
    PRO = "pro"           # 월 29,900원
    AGENCY = "agency"     # 월 99,900원

PLAN_LIMITS = {
    PlanType.FREE:   {"posts_per_month": 5,   "ai_rewrite": False, "seo_analysis": False, "naver_auto": False},
    PlanType.BASIC:  {"posts_per_month": 30,  "ai_rewrite": True,  "seo_analysis": True,  "naver_auto": False},
    PlanType.PRO:    {"posts_per_month": 150, "ai_rewrite": True,  "seo_analysis": True,  "naver_auto": True},
    PlanType.AGENCY: {"posts_per_month": 999, "ai_rewrite": True,  "seo_analysis": True,  "naver_auto": True},
}

PLAN_PRICES_KRW = {
    PlanType.FREE: 0,
    PlanType.BASIC: 9900,
    PlanType.PRO: 29900,
    PlanType.AGENCY: 99900,
}

def get_plan_limits(plan: PlanType) -> dict:
    return PLAN_LIMITS[plan]

def get_plan_price(plan: PlanType) -> int:
    return PLAN_PRICES_KRW[plan]
