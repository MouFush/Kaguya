"""
角色管理API
"""

from fastapi import APIRouter, HTTPException
from typing import List

from app.core.config import PRESET_ROLES
from app.models.schemas import Role, RoleListResponse

router = APIRouter()


@router.get("/roles", response_model=RoleListResponse)
async def get_roles():
    """获取所有角色列表"""
    return RoleListResponse(
        data=[Role(**role) for role in PRESET_ROLES],
        total=len(PRESET_ROLES)
    )


@router.get("/roles/{role_id}", response_model=Role)
async def get_role(role_id: str):
    """获取特定角色详情"""
    role = next((r for r in PRESET_ROLES if r["id"] == role_id), None)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return Role(**role)


@router.get("/roles/{role_id}/system-prompt")
async def get_role_system_prompt(role_id: str):
    """获取角色的系统提示词"""
    role = next((r for r in PRESET_ROLES if r["id"] == role_id), None)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"system_prompt": role.get("system", "")}
