"""
썸네일 이미지 생성 서비스
Pillow를 사용하여 블로그 썸네일을 자동으로 생성합니다.
한국어 텍스트를 지원하며 그라디언트 배경을 사용합니다.
"""
import logging
import os
import re
from typing import Optional, Tuple
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from app.config import settings

logger = logging.getLogger(__name__)

# 포스트 유형별 색상 팔레트 (그라디언트 시작/끝 색상)
COLOR_PALETTES = {
    "informational": [
        ((41, 128, 185), (109, 213, 250)),   # 파란색 계열
        ((39, 174, 96), (132, 220, 132)),     # 초록색 계열
        ((52, 73, 94), (100, 145, 160)),      # 다크 블루
    ],
    "review": [
        ((230, 126, 34), (253, 203, 110)),    # 주황색 계열
        ((192, 57, 43), (241, 148, 138)),     # 빨간색 계열
        ((211, 84, 0), (250, 177, 60)),       # 앰버 계열
    ],
    "comparison": [
        ((142, 68, 173), (200, 130, 220)),    # 보라색 계열
        ((41, 128, 185), (142, 68, 173)),     # 블루-보라 그라디언트
        ((52, 73, 94), (142, 68, 173)),       # 다크-보라
    ],
    "listicle": [
        ((22, 160, 133), (72, 201, 176)),     # 청록색 계열
        ((39, 174, 96), (22, 160, 133)),      # 초록-청록
        ((26, 188, 156), (72, 201, 176)),     # 민트 계열
    ],
}

# 이미지 크기 설정
THUMBNAIL_WIDTH = 1200
THUMBNAIL_HEIGHT = 630


class ImageGenerator:
    """블로그 썸네일 이미지 생성기"""

    def __init__(self):
        self.output_dir = settings.GENERATED_IMAGES_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self._font_cache: dict = {}

    def generate_thumbnail(
        self,
        title: str,
        keyword: str,
        post_type: str = "informational",
        custom_colors: Optional[Tuple[Tuple, Tuple]] = None,
    ) -> str:
        """
        블로그 썸네일 이미지 생성

        Args:
            title: 블로그 포스트 제목
            keyword: 주요 키워드
            post_type: 포스트 유형
            custom_colors: 커스텀 색상 (시작색, 끝색)

        Returns:
            생성된 이미지 파일 경로
        """
        # 이미지 생성
        img = Image.new("RGBA", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), color=(255, 255, 255, 255))

        # 그라디언트 배경 그리기
        colors = custom_colors or self._get_palette_colors(post_type, title)
        self._draw_gradient(img, colors[0], colors[1])

        # 장식 요소 추가
        draw = ImageDraw.Draw(img)
        self._draw_decorations(draw, post_type)

        # 텍스트 오버레이
        self._draw_text_overlay(draw, title, keyword, post_type)

        # 파일 저장
        filename = self._generate_filename(title)
        output_path = os.path.join(self.output_dir, filename)
        img = img.convert("RGB")
        img.save(output_path, "PNG", optimize=True)

        logger.info(f"썸네일 생성 완료: {output_path}")
        return output_path

    def _get_palette_colors(
        self, post_type: str, title: str
    ) -> Tuple[Tuple, Tuple]:
        """포스트 유형과 제목 기반으로 팔레트 색상 선택"""
        palettes = COLOR_PALETTES.get(post_type, COLOR_PALETTES["informational"])
        # 제목 해시로 일관된 색상 선택
        hash_val = abs(hash(title))
        palette = palettes[hash_val % len(palettes)]
        return palette

    def _draw_gradient(
        self,
        img: Image.Image,
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int],
    ):
        """대각선 그라디언트 배경 그리기"""
        width, height = img.size
        draw = ImageDraw.Draw(img)

        for i in range(width):
            ratio = i / width
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(i, 0), (i, height)], fill=(r, g, b))

    def _draw_decorations(self, draw: ImageDraw.Draw, post_type: str):
        """장식 도형 그리기"""
        # 우측 하단 큰 원 (반투명 효과 시뮬레이션)
        circle_color = (255, 255, 255, 30)
        # 큰 원
        draw.ellipse(
            [THUMBNAIL_WIDTH - 300, THUMBNAIL_HEIGHT - 300, THUMBNAIL_WIDTH + 100, THUMBNAIL_HEIGHT + 100],
            fill=(255, 255, 255, 20),
            outline=(255, 255, 255, 40),
            width=3,
        )
        # 중간 원
        draw.ellipse(
            [THUMBNAIL_WIDTH - 200, THUMBNAIL_HEIGHT - 200, THUMBNAIL_WIDTH + 50, THUMBNAIL_HEIGHT + 50],
            fill=None,
            outline=(255, 255, 255, 60),
            width=2,
        )
        # 좌측 상단 원
        draw.ellipse(
            [-100, -100, 250, 250],
            fill=None,
            outline=(255, 255, 255, 30),
            width=3,
        )

        # 하단 구분선
        draw.rectangle(
            [40, THUMBNAIL_HEIGHT - 80, THUMBNAIL_WIDTH - 40, THUMBNAIL_HEIGHT - 76],
            fill=(255, 255, 255, 60),
        )

    def _draw_text_overlay(
        self,
        draw: ImageDraw.Draw,
        title: str,
        keyword: str,
        post_type: str,
    ):
        """제목과 키워드 텍스트 오버레이"""
        # 폰트 로드
        title_font = self._load_font(size=56)
        keyword_font = self._load_font(size=32)
        badge_font = self._load_font(size=24)

        # 포스트 유형 뱃지
        type_labels = {
            "informational": "📝 정보",
            "review": "⭐ 리뷰",
            "comparison": "🔍 비교",
            "listicle": "📋 리스트",
        }
        type_label = type_labels.get(post_type, "📝 블로그")

        # 뱃지 배경
        draw.rounded_rectangle(
            [40, 40, 200, 85],
            radius=8,
            fill=(255, 255, 255, 50),
        )
        draw.text((55, 52), type_label, font=badge_font, fill=(255, 255, 255))

        # BlogPilot 워터마크
        draw.text(
            (THUMBNAIL_WIDTH - 160, 52),
            "BlogPilot",
            font=badge_font,
            fill=(255, 255, 255, 180),
        )

        # 키워드 텍스트
        keyword_text = f"#{keyword}"
        draw.text(
            (50, THUMBNAIL_HEIGHT - 70),
            keyword_text,
            font=keyword_font,
            fill=(255, 255, 255, 200),
        )

        # 제목 텍스트 (줄바꿈 처리)
        wrapped_title = self._wrap_text(title, max_chars=22)
        title_lines = wrapped_title.split("\n")

        # 제목 위치 계산 (수직 중앙 근처)
        line_height = 70
        total_height = len(title_lines) * line_height
        start_y = (THUMBNAIL_HEIGHT - total_height) // 2 - 20

        # 텍스트 그림자 효과
        for i, line in enumerate(title_lines):
            y_pos = start_y + i * line_height
            # 그림자
            draw.text((52, y_pos + 3), line, font=title_font, fill=(0, 0, 0, 100))
            # 실제 텍스트
            draw.text((50, y_pos), line, font=title_font, fill=(255, 255, 255))

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        """폰트 로드 (캐시 사용)"""
        cache_key = size
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = None

        # 시스템 한국어 폰트 경로 목록
        korean_font_paths = [
            # Windows
            "C:/Windows/Fonts/malgun.ttf",      # 맑은 고딕
            "C:/Windows/Fonts/NanumGothic.ttf",  # 나눔고딕
            "C:/Windows/Fonts/gulim.ttc",         # 굴림
            # Linux
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            # macOS
            "/System/Library/Fonts/AppleGothic.ttf",
            "/Library/Fonts/AppleGothic.ttf",
        ]

        for font_path in korean_font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, size)
                    break
                except Exception:
                    continue

        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

        self._font_cache[cache_key] = font
        return font

    def _wrap_text(self, text: str, max_chars: int = 22) -> str:
        """텍스트를 지정된 길이로 줄바꿈"""
        if len(text) <= max_chars:
            return text

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            if len(test_line) <= max_chars:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                # 단어 자체가 너무 길면 강제 분할
                if len(word) > max_chars:
                    lines.append(word[:max_chars])
                    current_line = word[max_chars:]
                else:
                    current_line = word

        if current_line:
            lines.append(current_line)

        # 최대 3줄로 제한
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1][: max_chars - 3] + "..."

        return "\n".join(lines)

    def _generate_filename(self, title: str) -> str:
        """이미지 파일명 생성"""
        # 한글/영문/숫자만 유지
        safe_title = re.sub(r"[^\w가-힣]", "_", title[:30])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"thumb_{safe_title}_{timestamp}.png"

    def get_image_url(self, image_path: str) -> str:
        """이미지 경로를 URL로 변환 (정적 파일 서빙용)"""
        filename = os.path.basename(image_path)
        return f"/generated_images/{filename}"


# 전역 인스턴스
image_generator = ImageGenerator()
