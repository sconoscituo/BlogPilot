"""
네이버 블로그 자동 포스팅 서비스
네이버 블로그 Open API 사용 (https://developers.naver.com)
OAuth 2.0 인증 후 블로그 포스트를 발행합니다.
"""
import logging
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

NAVER_BLOG_API_URL = "https://openapi.naver.com/blog/writePost.json"
NAVER_AUTH_BASE_URL = "https://nid.naver.com/oauth2.0"
NAVER_TOKEN_URL = f"{NAVER_AUTH_BASE_URL}/token"


async def get_naver_auth_url(client_id: str, redirect_uri: str) -> str:
    """
    네이버 OAuth 2.0 인증 URL 생성

    Args:
        client_id: 네이버 애플리케이션 Client ID
        redirect_uri: 인증 완료 후 리다이렉트될 URI

    Returns:
        네이버 로그인 인증 URL
    """
    import secrets
    state = secrets.token_urlsafe(16)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"{NAVER_AUTH_BASE_URL}/authorize?{urlencode(params)}"


async def exchange_naver_code_for_token(
    code: str,
    state: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    """
    인증 코드를 액세스 토큰으로 교환

    Args:
        code: 네이버 OAuth 인증 코드
        state: CSRF 방지용 상태값
        client_id: 네이버 애플리케이션 Client ID
        client_secret: 네이버 애플리케이션 Client Secret
        redirect_uri: 등록된 리다이렉트 URI

    Returns:
        액세스 토큰 정보 딕셔너리
    """
    params = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
        "state": state,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(NAVER_TOKEN_URL, data=params)
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            raise RuntimeError(f"토큰 발급 실패: {data.get('error_description', data['error'])}")

        logger.info("네이버 액세스 토큰 발급 완료")
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "token_type": data.get("token_type"),
            "expires_in": data.get("expires_in"),
        }

    except httpx.HTTPStatusError as e:
        logger.error("네이버 토큰 교환 실패: %s", e)
        raise RuntimeError(f"네이버 토큰 교환 실패: {str(e)}")


async def post_to_naver_blog(
    access_token: str,
    title: str,
    content: str,
    tags: list[str] = [],
) -> dict:
    """
    네이버 블로그에 포스트 발행

    Args:
        access_token: 네이버 OAuth 2.0 액세스 토큰
        title: 포스트 제목
        content: 포스트 본문 (HTML 가능)
        tags: 태그 목록 (최대 10개)

    Returns:
        발행 결과 딕셔너리
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    # 태그는 쉼표로 구분, 최대 10개
    tag_str = ",".join(tags[:10]) if tags else ""

    data = {
        "title": title,
        "contents": content,
    }
    if tag_str:
        data["tags"] = tag_str

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                NAVER_BLOG_API_URL,
                data=data,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()

        logger.info("네이버 블로그 포스트 발행 완료: %s", title)
        return {
            "success": True,
            "title": title,
            "result": result,
        }

    except httpx.HTTPStatusError as e:
        error_detail = ""
        try:
            error_detail = e.response.json().get("errorMessage", str(e))
        except Exception:
            error_detail = str(e)
        logger.error("네이버 블로그 발행 실패: %s", error_detail)
        raise RuntimeError(f"네이버 블로그 발행 실패: {error_detail}")

    except Exception as e:
        logger.error("네이버 블로그 발행 오류: %s", e)
        raise RuntimeError(f"네이버 블로그 발행 오류: {str(e)}")
