"""Tags API routes."""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_session
from backend.models.tag import Tag
from backend.repositories.tag_repository import TagRepository


router = APIRouter()


class TagCreate(BaseModel):
    """Schema for creating a tag."""
    name: str
    color: Optional[str] = "#000000"


class TagResponse(BaseModel):
    """Schema for tag response."""
    id: int
    name: str
    color: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=TagResponse)
async def create_tag(tag: TagCreate):
    """Create a new tag."""
    with get_session().__enter__() as session:
        repo = TagRepository(session)
        
        # Check if tag already exists
        existing = repo.get_by_name(tag.name)
        if existing:
            raise HTTPException(status_code=400, detail="Tag already exists")
        
        new_tag = repo.create(
            name=tag.name,
            color=tag.color,
        )
        
        return TagResponse.model_validate(new_tag)


@router.get("/", response_model=List[TagResponse])
async def list_tags():
    """List all tags."""
    with get_session().__enter__() as session:
        repo = TagRepository(session)
        tags = repo.get_all()
        return [TagResponse.model_validate(tag) for tag in tags]


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int):
    """Get a specific tag by ID."""
    with get_session().__enter__() as session:
        repo = TagRepository(session)
        tag = repo.get_by_id(tag_id)
        
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        return TagResponse.model_validate(tag)


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int):
    """Delete a tag."""
    with get_session().__enter__() as session:
        repo = TagRepository(session)
        tag = repo.get_by_id(tag_id)
        
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        repo.delete(tag)
        return {"message": "Tag deleted successfully"}
