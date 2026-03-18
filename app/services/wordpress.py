"""
WordPress REST API 클라이언트
Application Passwords 인증을 사용하여 WordPress에 포스트를 발행합니다.
"""
import base64
import logging
import mimetypes
import os
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WordPressClient:
    """WordPress REST API 클라이언트"""

    def __init__(self):
        self.base_url = settings.wordpress_api_url
        self.username = settings.WORDPRESS_USERNAME
        self.app_password = settings.WORDPRESS_APP_PASSWORD
        self._auth_header = self._build_auth_header()

    def _build_auth_header(self) -> dict:
        """Application Password 기반 인증 헤더 생성"""
        if not self.username or not self.app_password:
            return {}
        credentials = f"{self.username}:{self.app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    @property
    def _headers(self) -> dict:
        """기본 요청 헤더"""
        return {
            **self._auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def test_connection(self) -> dict:
        """
        WordPress 연결 테스트

        Returns:
            연결 상태 정보
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/users/me",
                    headers=self._headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "user_id": data.get("id"),
                        "username": data.get("name"),
                        "site_url": settings.WORDPRESS_URL,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"인증 실패: HTTP {response.status_code}",
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_post(
        self,
        title: str,
        content: str,
        status: str = "publish",
        slug: Optional[str] = None,
        excerpt: Optional[str] = None,
        categories: Optional[list[int]] = None,
        tags: Optional[list[int]] = None,
        featured_media: Optional[int] = None,
        meta: Optional[dict] = None,
    ) -> dict:
        """
        WordPress 포스트 생성/발행

        Args:
            title: 포스트 제목
            content: HTML 콘텐츠
            status: 상태 (publish/draft/future)
            slug: URL 슬러그
            excerpt: 요약문
            categories: 카테고리 ID 목록
            tags: 태그 ID 목록
            featured_media: 대표 이미지 미디어 ID
            meta: 메타 데이터 딕셔너리

        Returns:
            생성된 포스트 정보
        """
        if not settings.is_wordpress_configured:
            raise ValueError("WordPress가 설정되지 않았습니다. .env 파일을 확인하세요.")

        payload = {
            "title": title,
            "content": content,
            "status": status,
        }

        if slug:
            payload["slug"] = slug
        if excerpt:
            payload["excerpt"] = excerpt
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags
        if featured_media:
            payload["featured_media"] = featured_media
        if meta:
            payload["meta"] = meta

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/posts",
                    json=payload,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"WordPress 포스트 발행 완료: ID={data.get('id')}, URL={data.get('link')}")
                return {
                    "success": True,
                    "post_id": data.get("id"),
                    "url": data.get("link"),
                    "status": data.get("status"),
                    "slug": data.get("slug"),
                }

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("message", str(e))
            except Exception:
                error_detail = str(e)
            logger.error(f"WordPress 포스트 발행 실패: {error_detail}")
            raise RuntimeError(f"WordPress 발행 실패: {error_detail}")

        except Exception as e:
            logger.error(f"WordPress 연결 오류: {e}")
            raise RuntimeError(f"WordPress 연결 오류: {str(e)}")

    async def update_post(self, post_id: int, **kwargs) -> dict:
        """기존 WordPress 포스트 수정"""
        if not settings.is_wordpress_configured:
            raise ValueError("WordPress가 설정되지 않았습니다.")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.patch(
                    f"{self.base_url}/posts/{post_id}",
                    json=kwargs,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "success": True,
                    "post_id": data.get("id"),
                    "url": data.get("link"),
                }
        except Exception as e:
            raise RuntimeError(f"WordPress 포스트 수정 실패: {str(e)}")

    async def upload_media(self, file_path: str, alt_text: str = "") -> dict:
        """
        WordPress 미디어 라이브러리에 이미지 업로드

        Args:
            file_path: 업로드할 파일 경로
            alt_text: 이미지 대체 텍스트

        Returns:
            업로드된 미디어 정보
        """
        if not settings.is_wordpress_configured:
            raise ValueError("WordPress가 설정되지 않았습니다.")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {file_path}")

        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "image/png"

        upload_headers = {
            **self._auth_header,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": mime_type,
        }

        try:
            with open(file_path, "rb") as f:
                file_content = f.read()

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/media",
                    content=file_content,
                    headers=upload_headers,
                )
                response.raise_for_status()
                data = response.json()

                media_id = data.get("id")

                # 대체 텍스트 업데이트
                if alt_text and media_id:
                    await client.patch(
                        f"{self.base_url}/media/{media_id}",
                        json={"alt_text": alt_text},
                        headers=self._headers,
                    )

                logger.info(f"이미지 업로드 완료: ID={media_id}")
                return {
                    "success": True,
                    "media_id": media_id,
                    "url": data.get("source_url"),
                }

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("message", str(e))
            except Exception:
                error_detail = str(e)
            raise RuntimeError(f"미디어 업로드 실패: {error_detail}")

        except Exception as e:
            raise RuntimeError(f"미디어 업로드 오류: {str(e)}")

    async def get_categories(self) -> list[dict]:
        """WordPress 카테고리 목록 조회"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/categories",
                    params={"per_page": 100},
                    headers=self._headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"카테고리 조회 실패: {e}")
            return []

    async def get_tags(self) -> list[dict]:
        """WordPress 태그 목록 조회"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/tags",
                    params={"per_page": 100},
                    headers=self._headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"태그 조회 실패: {e}")
            return []

    async def create_tag(self, name: str) -> Optional[int]:
        """새 태그 생성 후 ID 반환"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/tags",
                    json={"name": name},
                    headers=self._headers,
                )
                if response.status_code in (200, 201):
                    return response.json().get("id")
                # 이미 존재하는 태그인 경우
                elif response.status_code == 400:
                    existing = await self.get_tags()
                    for tag in existing:
                        if tag.get("name", "").lower() == name.lower():
                            return tag.get("id")
        except Exception as e:
            logger.warning(f"태그 생성 실패: {e}")
        return None

    async def get_post(self, post_id: int) -> Optional[dict]:
        """WordPress 포스트 상세 조회"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/posts/{post_id}",
                    headers=self._headers,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"포스트 조회 실패: {e}")
        return None


# 전역 인스턴스
wordpress_client = WordPressClient()
