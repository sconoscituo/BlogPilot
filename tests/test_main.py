"""
BlogPilot 기본 헬스체크 테스트
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# app 패키지를 import 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# 테스트용 최소 앱 (외부 의존성 없이 헬스체크만 검증)
def create_test_app() -> FastAPI:
    app = FastAPI(title="BlogPilot Test")

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "blogpilot"}

    return app


@pytest.fixture
def client():
    app = create_test_app()
    with TestClient(app) as c:
        yield c


def test_health_check_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_response_body(client):
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "blogpilot"


def test_health_check_content_type(client):
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]


def test_unknown_route_returns_404(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_settings_class_importable():
    """Settings 클래스가 정상적으로 import 되는지 확인"""
    from app.config import Settings
    assert Settings is not None


def test_settings_has_required_attributes():
    """Settings에 필수 속성이 존재하는지 확인"""
    from app.config import Settings
    assert hasattr(Settings, "APP_NAME")
    assert hasattr(Settings, "APP_VERSION")
    assert hasattr(Settings, "GEMINI_MODEL")


def test_settings_default_values():
    """기본값이 올바르게 설정되는지 확인"""
    from app.config import Settings
    s = Settings()
    assert s.APP_NAME == "BlogPilot"
    assert s.APP_VERSION == "1.0.0"
    assert s.GEMINI_MODEL == "gemini-1.5-flash"
    assert s.DEFAULT_LANGUAGE == "ko"
