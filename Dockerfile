FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (Pillow 및 한국어 폰트 지원)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    fonts-nanum \
    fonts-nanum-coding \
    && rm -rf /var/lib/apt/lists/*

# 한국어 폰트 캐시 갱신
RUN fc-cache -f -v

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 이미지 저장 디렉토리 생성
RUN mkdir -p /app/generated_images

# 비루트 사용자 생성 (보안)
RUN useradd -m -u 1000 blogpilot && \
    chown -R blogpilot:blogpilot /app
USER blogpilot

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# 앱 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
