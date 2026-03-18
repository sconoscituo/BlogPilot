"""
구글 애드센스 수익 대시보드 서비스
Google AdSense API를 통해 수익, 페이지뷰, CPC, RPM 데이터를 조회합니다.
"""
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class AdSenseService:
    """Google AdSense API 연동 서비스"""

    def __init__(self):
        self._service = None

    def _get_service(self):
        """AdSense API 서비스 객체 반환 (지연 초기화)"""
        if self._service is not None:
            return self._service

        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account

            from app.config import settings
            creds_path = settings.GOOGLE_SEARCH_CONSOLE_CREDENTIALS

            if not creds_path or not os.path.exists(creds_path):
                logger.warning("애드센스 자격증명 파일이 설정되지 않았습니다.")
                return None

            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/adsense.readonly"],
            )
            self._service = build("adsense", "v2", credentials=credentials)
            return self._service
        except Exception as e:
            logger.error(f"AdSense 서비스 초기화 실패: {e}")
            return None

    async def get_revenue_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """
        수익 데이터 조회 (일별/월별 수익, 페이지뷰, CPC, RPM)

        Args:
            start_date: 조회 시작일 (YYYY-MM-DD), 기본 30일 전
            end_date: 조회 종료일 (YYYY-MM-DD), 기본 오늘

        Returns:
            일별 수익, 월간 합계, 페이지별 수익 데이터
        """
        if not end_date:
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        service = self._get_service()
        if service is None:
            return self._get_demo_data(start_date, end_date)

        try:
            from app.config import settings
            account_id = settings.ADSENSE_ACCOUNT_ID

            # 일별 수익 리포트
            daily_report = (
                service.accounts()
                .reports()
                .generate(
                    account=f"accounts/{account_id}",
                    dateRange="CUSTOM",
                    startDate_year=int(start_date[:4]),
                    startDate_month=int(start_date[5:7]),
                    startDate_day=int(start_date[8:10]),
                    endDate_year=int(end_date[:4]),
                    endDate_month=int(end_date[5:7]),
                    endDate_day=int(end_date[8:10]),
                    dimensions=["DATE"],
                    metrics=["ESTIMATED_EARNINGS", "PAGE_VIEWS", "CLICKS", "PAGE_VIEWS_RPM", "COST_PER_CLICK"],
                )
                .execute()
            )

            daily_data = []
            rows = daily_report.get("rows", [])
            for row in rows:
                cells = row.get("cells", [])
                daily_data.append({
                    "date": cells[0].get("value", "") if len(cells) > 0 else "",
                    "earnings": float(cells[1].get("value", 0)) if len(cells) > 1 else 0.0,
                    "pageviews": int(cells[2].get("value", 0)) if len(cells) > 2 else 0,
                    "clicks": int(cells[3].get("value", 0)) if len(cells) > 3 else 0,
                    "rpm": float(cells[4].get("value", 0)) if len(cells) > 4 else 0.0,
                    "cpc": float(cells[5].get("value", 0)) if len(cells) > 5 else 0.0,
                })

            total_earnings = sum(d["earnings"] for d in daily_data)
            total_pageviews = sum(d["pageviews"] for d in daily_data)
            total_clicks = sum(d["clicks"] for d in daily_data)
            avg_rpm = (sum(d["rpm"] for d in daily_data) / len(daily_data)) if daily_data else 0.0
            avg_cpc = (sum(d["cpc"] for d in daily_data) / len(daily_data)) if daily_data else 0.0

            # 월별 합계
            monthly_summary = self._aggregate_monthly(daily_data)

            return {
                "daily": daily_data,
                "monthly": monthly_summary,
                "totals": {
                    "earnings": round(total_earnings, 2),
                    "pageviews": total_pageviews,
                    "clicks": total_clicks,
                    "avg_rpm": round(avg_rpm, 2),
                    "avg_cpc": round(avg_cpc, 2),
                },
                "start_date": start_date,
                "end_date": end_date,
                "is_demo": False,
            }
        except Exception as e:
            logger.error(f"AdSense 데이터 조회 실패: {e}")
            return self._get_demo_data(start_date, end_date)

    def _aggregate_monthly(self, daily_data: list) -> list:
        """일별 데이터를 월별로 집계"""
        monthly = {}
        for row in daily_data:
            date_str = row["date"]
            if len(date_str) >= 7:
                month_key = date_str[:7]  # YYYY-MM
                if month_key not in monthly:
                    monthly[month_key] = {"month": month_key, "earnings": 0.0, "pageviews": 0, "clicks": 0}
                monthly[month_key]["earnings"] += row["earnings"]
                monthly[month_key]["pageviews"] += row["pageviews"]
                monthly[month_key]["clicks"] += row["clicks"]

        result = list(monthly.values())
        for m in result:
            m["earnings"] = round(m["earnings"], 2)
        return sorted(result, key=lambda x: x["month"])

    def _get_demo_data(self, start_date: str, end_date: str) -> dict:
        """API 미설정 시 데모 데이터 반환"""
        random.seed(7)
        daily_data = []
        base_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        current = base_date

        while current <= end_dt:
            # 주말에 약간 더 높은 수익
            is_weekend = current.weekday() >= 5
            base_earnings = random.uniform(2.5, 8.0) if is_weekend else random.uniform(1.5, 6.0)
            pageviews = random.randint(300, 1200) if is_weekend else random.randint(200, 900)
            clicks = random.randint(5, 25)
            rpm = base_earnings / pageviews * 1000
            cpc = base_earnings / max(clicks, 1)

            daily_data.append({
                "date": current.strftime("%Y-%m-%d"),
                "earnings": round(base_earnings, 2),
                "pageviews": pageviews,
                "clicks": clicks,
                "rpm": round(rpm, 2),
                "cpc": round(cpc, 2),
            })
            current += timedelta(days=1)

        total_earnings = sum(d["earnings"] for d in daily_data)
        total_pageviews = sum(d["pageviews"] for d in daily_data)
        total_clicks = sum(d["clicks"] for d in daily_data)
        avg_rpm = (sum(d["rpm"] for d in daily_data) / len(daily_data)) if daily_data else 0.0
        avg_cpc = (sum(d["cpc"] for d in daily_data) / len(daily_data)) if daily_data else 0.0

        # 페이지별 수익 데모
        page_revenue = [
            {"page": "/블로그-수익화-방법", "earnings": 18.42, "pageviews": 2340, "rpm": 7.87},
            {"page": "/애드센스-승인-조건", "earnings": 15.30, "pageviews": 1980, "rpm": 7.73},
            {"page": "/SEO-최적화-가이드", "earnings": 12.88, "pageviews": 2100, "rpm": 6.13},
            {"page": "/키워드-리서치-방법", "earnings": 11.20, "pageviews": 1650, "rpm": 6.79},
            {"page": "/워드프레스-시작하기", "earnings": 9.75, "pageviews": 1420, "rpm": 6.87},
        ]

        return {
            "daily": daily_data,
            "monthly": self._aggregate_monthly(daily_data),
            "totals": {
                "earnings": round(total_earnings, 2),
                "pageviews": total_pageviews,
                "clicks": total_clicks,
                "avg_rpm": round(avg_rpm, 2),
                "avg_cpc": round(avg_cpc, 2),
            },
            "page_revenue": page_revenue,
            "start_date": start_date,
            "end_date": end_date,
            "is_demo": True,
        }


# 전역 인스턴스
adsense_service = AdSenseService()
