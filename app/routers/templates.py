"""
글 템플릿 관리 API 라우터
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.template import Template

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/templates", tags=["템플릿"])


class TemplateCreate(BaseModel):
    name: str
    template_type: str
    description: Optional[str] = None
    system_prompt: str
    user_prompt_template: str
    min_word_count: int = 1500
    max_word_count: int = 3000
    include_faq: bool = True
    include_toc: bool = True
    keyword_density_target: float = 1.5
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    min_word_count: Optional[int] = None
    max_word_count: Optional[int] = None
    include_faq: Optional[bool] = None
    include_toc: Optional[bool] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


@router.get("/")
async def list_templates(
    template_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """템플릿 목록 조회"""
    query = select(Template).order_by(Template.is_default.desc(), Template.usage_count.desc())

    if template_type:
        query = query.where(Template.template_type == template_type)
    if is_active is not None:
        query = query.where(Template.is_active == is_active)

    result = await db.execute(query)
    templates = result.scalars().all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "template_type": t.template_type,
            "description": t.description,
            "min_word_count": t.min_word_count,
            "max_word_count": t.max_word_count,
            "include_faq": t.include_faq,
            "include_toc": t.include_toc,
            "keyword_density_target": t.keyword_density_target,
            "is_active": t.is_active,
            "is_default": t.is_default,
            "usage_count": t.usage_count,
            "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ]


@router.post("/", status_code=201)
async def create_template(
    template_data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """새 템플릿 생성"""
    # 기본 템플릿으로 설정 시 기존 기본 템플릿 해제
    if template_data.is_default:
        result = await db.execute(
            select(Template).where(
                Template.template_type == template_data.template_type,
                Template.is_default == True,
            )
        )
        existing_defaults = result.scalars().all()
        for t in existing_defaults:
            t.is_default = False

    template = Template(**template_data.model_dump())
    db.add(template)
    await db.flush()
    await db.refresh(template)

    return {"message": "템플릿 생성 완료", "template_id": template.id}


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """템플릿 상세 조회"""
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")

    return {
        "id": template.id,
        "name": template.name,
        "template_type": template.template_type,
        "description": template.description,
        "system_prompt": template.system_prompt,
        "user_prompt_template": template.user_prompt_template,
        "min_word_count": template.min_word_count,
        "max_word_count": template.max_word_count,
        "include_faq": template.include_faq,
        "include_toc": template.include_toc,
        "keyword_density_target": template.keyword_density_target,
        "use_schema_markup": template.use_schema_markup,
        "is_active": template.is_active,
        "is_default": template.is_default,
        "usage_count": template.usage_count,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat(),
    }


@router.patch("/{template_id}")
async def update_template(
    template_id: int,
    updates: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """템플릿 수정"""
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.flush()
    return {"message": "템플릿 수정 완료"}


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """템플릿 삭제"""
    result = await db.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")

    await db.delete(template)


@router.post("/seed-defaults")
async def seed_default_templates(db: AsyncSession = Depends(get_db)):
    """기본 템플릿 초기 데이터 삽입"""
    from app.content_templates_data import DEFAULT_TEMPLATES

    created = 0
    for tmpl_data in DEFAULT_TEMPLATES:
        existing = await db.execute(
            select(Template).where(Template.name == tmpl_data["name"])
        )
        if not existing.scalar_one_or_none():
            template = Template(**tmpl_data)
            db.add(template)
            created += 1

    await db.flush()
    return {"message": f"{created}개 기본 템플릿 생성 완료"}
