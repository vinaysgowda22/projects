"""Settings API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_session
from backend.models.setting import Setting
from backend.repositories.setting_repository import SettingRepository


router = APIRouter()


class SettingCreate(BaseModel):
    """Schema for creating/updating a setting."""
    key: str
    value: str


class SettingResponse(BaseModel):
    """Schema for setting response."""
    id: int
    key: str
    value: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=SettingResponse)
async def create_setting(setting: SettingCreate):
    """Create a new setting."""
    with get_session().__enter__() as session:
        repo = SettingRepository(session)
        
        # Check if setting already exists
        existing = repo.get_by_key(setting.key)
        if existing:
            raise HTTPException(status_code=400, detail="Setting already exists")
        
        new_setting = repo.create(
            key=setting.key,
            value=setting.value,
        )
        
        return SettingResponse.model_validate(new_setting)


@router.put("/{key}", response_model=SettingResponse)
async def upsert_setting(key: str, setting: SettingCreate):
    """Create or update a setting."""
    with get_session().__enter__() as session:
        repo = SettingRepository(session)
        
        upserted = repo.upsert(key, setting.value)
        return SettingResponse.model_validate(upserted)


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str):
    """Get a specific setting by key."""
    with get_session().__enter__() as session:
        repo = SettingRepository(session)
        setting = repo.get_by_key(key)
        
        if not setting:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        return SettingResponse.model_validate(setting)


@router.get("/", response_model=list[SettingResponse])
async def list_settings():
    """List all settings."""
    with get_session().__enter__() as session:
        repo = SettingRepository(session)
        settings = repo.get_all()
        return [SettingResponse.model_validate(s) for s in settings]


@router.delete("/{key}")
async def delete_setting(key: str):
    """Delete a setting."""
    with get_session().__enter__() as session:
        repo = SettingRepository(session)
        setting = repo.get_by_key(key)
        
        if not setting:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        repo.delete(setting)
        return {"message": "Setting deleted successfully"}
