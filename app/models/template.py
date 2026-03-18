"""
글 템플릿 모델
Gemini 프롬프트 템플릿과 글 구조를 저장합니다.
"""
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Template(Base):
    """글 작성 템플릿 모델"""
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 템플릿 기본 정보
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="템플릿 이름")
    template_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="유형 (informational/review/comparison/listicle)")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="템플릿 설명")

    # Gemini 프롬프트
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="시스템 프롬프트")
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False, comment="사용자 프롬프트 템플릿")

    # 글 구조 설정
    min_word_count: Mapped[int] = mapped_column(Integer, default=1500, comment="최소 단어 수")
    max_word_count: Mapped[int] = mapped_column(Integer, default=3000, comment="최대 단어 수")
    include_faq: Mapped[bool] = mapped_column(Boolean, default=True, comment="FAQ 섹션 포함 여부")
    include_toc: Mapped[bool] = mapped_column(Boolean, default=True, comment="목차 포함 여부")

    # SEO 설정
    keyword_density_target: Mapped[float] = mapped_column(default=1.5, comment="목표 키워드 밀도 (%)")
    use_schema_markup: Mapped[bool] = mapped_column(Boolean, default=False, comment="스키마 마크업 사용")

    # 상태
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성 여부")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="기본 템플릿 여부")
    usage_count: Mapped[int] = mapped_column(Integer, default=0, comment="사용 횟수")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id} name='{self.name}' type={self.template_type}>"
