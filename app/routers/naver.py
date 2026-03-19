"""
네이버 블로그 OAuth 및 포스팅 라우터
엔드포인트:
  GET  /auth/naver           — 네이버 OAuth 인증 시작 (로그인 URL 리다이렉트)
  GET  /auth/naver/callback  — OAuth 콜백 처리 (코드 → 액세스 토큰)
  POST /posts/naver          — 네이버 블로그 포스트 발행
"""
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import settings
from app.services.naver_blog import (
    exchange_naver_code_for_token,
    get_naver_auth_url,
    post_to_naver_blog,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["네이버 블로그"])


# ─────────────────────────────────────────────
# 요청/응답 스키마
# ─────────────────────────────────────────────

class NaverPostRequest(BaseModel):
    access_token: str
    title: str
    content: str
    tags: list[str] = []


class NaverPostResponse(BaseModel):
    success: bool
    title: str
    message: str


# ─────────────────────────────────────────────
# 네이버 OAuth 설정 헬퍼
# ─────────────────────────────────────────────

def _get_naver_credentials() -> tuple[str, str, str]:
    """설정에서 네이버 자격증명 반환. 미설정 시 예외 발생."""
    client_id = getattr(settings, "NAVER_CLIENT_ID", "")
    client_secret = getattr(settings, "NAVER_CLIENT_SECRET", "")
    redirect_uri = getattr(settings, "NAVER_REDIRECT_URI", "")

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="네이버 API 설정이 완료되지 않았습니다. .env 파일에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 설정하세요.",
        )
    if not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail="NAVER_REDIRECT_URI가 설정되지 않았습니다.",
        )
    return client_id, client_secret, redirect_uri


# ─────────────────────────────────────────────
# 엔드포인트
# ─────────────────────────────────────────────

@router.get("/auth/naver", summary="네이버 OAuth 인증 시작")
async def naver_auth_start():
    """
    네이버 OAuth 2.0 인증을 시작합니다.
    네이버 로그인 페이지로 리다이렉트합니다.
    """
    client_id, _, redirect_uri = _get_naver_credentials()
    auth_url = await get_naver_auth_url(client_id=client_id, redirect_uri=redirect_uri)
    return RedirectResponse(url=auth_url)


@router.get("/auth/naver/callback", summary="네이버 OAuth 콜백 처리")
async def naver_auth_callback(
    code: str = Query(..., description="네이버가 전달한 인증 코드"),
    state: str = Query(..., description="CSRF 방지용 상태값"),
    error: str = Query(None, description="오류 코드 (인증 거부 시)"),
    error_description: str = Query(None, description="오류 설명"),
):
    """
    네이버 OAuth 콜백을 처리하고 액세스 토큰을 반환합니다.
    실제 서비스에서는 토큰을 세션 또는 DB에 저장해야 합니다.
    """
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"네이버 인증 거부: {error_description or error}",
        )

    client_id, client_secret, redirect_uri = _get_naver_credentials()

    try:
        token_data = await exchange_naver_code_for_token(
            code=code,
            state=state,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "success": True,
        "message": "네이버 인증이 완료되었습니다. access_token을 안전하게 보관하세요.",
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_in": token_data.get("expires_in"),
    }


@router.post(
    "/posts/naver",
    response_model=NaverPostResponse,
    summary="네이버 블로그 포스트 발행",
)
async def publish_to_naver(request: NaverPostRequest):
    """
    네이버 블로그에 포스트를 발행합니다.

    - **access_token**: 네이버 OAuth 액세스 토큰
    - **title**: 포스트 제목
    - **content**: 포스트 본문 (HTML 가능)
    - **tags**: 태그 목록 (선택, 최대 10개)
    """
    if not request.access_token:
        raise HTTPException(status_code=400, detail="access_token이 필요합니다.")
    if not request.title or not request.content:
        raise HTTPException(status_code=400, detail="title과 content는 필수입니다.")

    try:
        await post_to_naver_blog(
            access_token=request.access_token,
            title=request.title,
            content=request.content,
            tags=request.tags,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return NaverPostResponse(
        success=True,
        title=request.title,
        message="네이버 블로그 포스트가 성공적으로 발행되었습니다.",
    )
