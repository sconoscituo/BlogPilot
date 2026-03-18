"""
구글 서치 콘솔 연동 서비스
Google Search Console API를 통해 키워드 성과 데이터를 조회합니다.
"""
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class SearchConsoleService:
    """Google Search Console API 연동 서비스"""

    def __init__(self):
        self._service = None

    def _get_service(self):
        """Search Console API 서비스 객체 반환 (지연 초기화)"""
        if self._service is not None:
            return self._service

        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account

            from app.config import settings
            creds_path = settings.GOOGLE_SEARCH_CONSOLE_CREDENTIALS
            site_url = settings.SEARCH_CONSOLE_SITE_URL

            if not creds_path or not os.path.exists(creds_path):
                logger.warning("서치 콘솔 자격증명 파일이 설정되지 않았습니다.")
                return None

            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
            )
            self._service = build("searchconsole", "v1", credentials=credentials)
            return self._service
        except Exception as e:
            logger.error(f"Search Console 서비스 초기화 실패: {e}")
            return None

    async def get_search_performance(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        row_limit: int = 50,
    ) -> dict:
        """
        키워드별 검색 성과 데이터 조회

        Args:
            start_date: 조회 시작일 (YYYY-MM-DD), 기본 28일 전
            end_date: 조회 종료일 (YYYY-MM-DD), 기본 오늘
            row_limit: 반환할 행 수

        Returns:
            키워드별 클릭수, 노출수, CTR, 평균 순위 데이터
        """
        # 날짜 기본값 설정
        if not end_date:
            end_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")

        service = self._get_service()
        if service is None:
            # API 미설정 시 데모 데이터 반환
            return self._get_demo_data(start_date, end_date)

        try:
            from app.config import settings
            site_url = settings.SEARCH_CONSOLE_SITE_URL

            request_body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": row_limit,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            }

            response = (
                service.searchanalytics()
                .query(siteUrl=site_url, body=request_body)
                .execute()
            )

            rows = response.get("rows", [])
            keywords = []
            for row in rows:
                keywords.append({
                    "keyword": row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": round(row.get("ctr", 0) * 100, 2),
                    "position": round(row.get("position", 0), 1),
                })

            # 날짜별 추이 데이터
            trend_data = await self._get_date_trend(service, start_date, end_date)

            return {
                "keywords": keywords,
                "trend": trend_data,
                "start_date": start_date,
                "end_date": end_date,
                "is_demo": False,
            }
        except Exception as e:
            logger.error(f"Search Console 데이터 조회 실패: {e}")
            return self._get_demo_data(start_date, end_date)

    async def _get_date_trend(self, service, start_date: str, end_date: str) -> list:
        """날짜별 클릭수/노출수 추이 조회"""
        try:
            from app.config import settings
            site_url = settings.SEARCH_CONSOLE_SITE_URL

            request_body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["date"],
                "rowLimit": 90,
                "orderBy": [{"fieldName": "date", "sortOrder": "ASCENDING"}],
            }
            response = (
                service.searchanalytics()
                .query(siteUrl=site_url, body=request_body)
                .execute()
            )
            rows = response.get("rows", [])
            return [
                {
                    "date": row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"날짜 추이 조회 실패: {e}")
            return []

    def _get_demo_data(self, start_date: str, end_date: str) -> dict:
        """API 미설정 시 데모 데이터 반환"""
        demo_keywords = [
            {"keyword": "블로그 수익화 방법", "clicks": 312, "impressions": 4820, "ctr": 6.47, "position": 3.2},
            {"keyword": "애드센스 승인 조건", "clicks": 287, "impressions": 5103, "ctr": 5.62, "position": 4.1},
            {"keyword": "티스토리 블로그 만들기", "clicks": 241, "impressions": 3940, "ctr": 6.12, "position": 2.8},
            {"keyword": "SEO 최적화 방법", "clicks": 198, "impressions": 6720, "ctr": 2.95, "position": 7.4},
            {"keyword": "키워드 리서치 도구", "clicks": 176, "impressions": 3210, "ctr": 5.48, "position": 5.1},
            {"keyword": "블로그 글쓰기 팁", "clicks": 154, "impressions": 2870, "ctr": 5.37, "position": 3.9},
            {"keyword": "구글 애널리틱스 사용법", "clicks": 132, "impressions": 4150, "ctr": 3.18, "position": 6.2},
            {"keyword": "워드프레스 블로그 시작", "clicks": 119, "impressions": 2340, "ctr": 5.09, "position": 4.7},
            {"keyword": "네이버 블로그 수익", "clicks": 98, "impressions": 1980, "ctr": 4.95, "position": 5.8},
            {"keyword": "콘텐츠 마케팅 전략", "clicks": 87, "impressions": 3560, "ctr": 2.44, "position": 8.3},
        ]

        # 데모 추이 데이터 (최근 28일)
        trend = []
        base_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        current = base_date
        import random
        random.seed(42)
        while current <= end_dt:
            trend.append({
                "date": current.strftime("%Y-%m-%d"),
                "clicks": random.randint(80, 200),
                "impressions": random.randint(1200, 3000),
            })
            current += timedelta(days=1)

        return {
            "keywords": demo_keywords,
            "trend": trend,
            "start_date": start_date,
            "end_date": end_date,
            "is_demo": True,
        }


# 전역 인스턴스
search_console_service = SearchConsoleService()
