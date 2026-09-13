"""AI provider API schemas. Raw credentials are never part of a response."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ProviderStatus


class ProviderCreateRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    model: str = Field(min_length=1, max_length=128)
    api_key: str = Field(min_length=1, max_length=512)
    base_url: str | None = Field(default=None, max_length=255)
    enabled: bool = True
    make_default: bool = False


class ProviderUpdateRequest(BaseModel):
    model: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(default=None, max_length=512)
    base_url: str | None = Field(default=None, max_length=255)
    enabled: bool | None = None


class ProviderSchema(BaseModel):
    id: uuid.UUID
    provider: str
    model: str
    base_url: str | None
    configured: bool
    api_key_masked: str | None
    enabled: bool
    is_default: bool
    status: ProviderStatus
    last_tested_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class ProviderModelSchema(BaseModel):
    id: str
    label: str | None = None


class ProviderTestResponse(BaseModel):
    ok: bool
    status: str
    detail: str | None = None
    models: list[ProviderModelSchema] = Field(default_factory=list)


class ProviderCatalogItem(BaseModel):
    key: str
    requires_base_url: bool
    default_base_url: str | None = None


class ProviderCatalogSchema(BaseModel):
    items: list[ProviderCatalogItem]
