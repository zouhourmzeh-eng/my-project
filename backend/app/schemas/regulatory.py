from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

from app.models.models import RegulatorySourceType, SeverityLevel, RegulatoryImpactStatus

# Regulatory Source Schemas

class RegulatorySourceBase(BaseModel):
    name: str
    url: str
    source_type: RegulatorySourceType
    parser_name: str
    frequency_hours: int = 24
    is_active: bool = True

class RegulatorySourceCreate(RegulatorySourceBase):
    pass

class RegulatorySourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[RegulatorySourceType] = None
    parser_name: Optional[str] = None
    frequency_hours: Optional[int] = None
    is_active: Optional[bool] = None

class RegulatorySourceOut(RegulatorySourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Project Regulation Schemas

class ProjectRegulationBase(BaseModel):
    regulation_name: str
    version: str = ""
    justification: str = ""

class ProjectRegulationCreate(ProjectRegulationBase):
    project_id: int

class ProjectRegulationOut(ProjectRegulationBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Regulatory Update Schemas

class RegulatoryUpdateBase(BaseModel):
    title: str
    publication_date: datetime
    original_url: str
    summary: str = ""
    extracted_requirements: str = ""
    severity: SeverityLevel

class RegulatoryUpdateCreate(RegulatoryUpdateBase):
    source_id: int

class RegulatoryUpdateOut(RegulatoryUpdateBase):
    id: int
    source_id: int
    created_at: datetime
    source: Optional[RegulatorySourceOut] = None

    class Config:
        from_attributes = True


# Regulatory Impact Schemas

class RegulatoryImpactBase(BaseModel):
    impact_summary: str = ""
    impact_justification: str = ""
    impacted_areas: str = "[]"  # JSON string
    standards_updated: str = "[]" # JSON string
    procedures_impacted: str = "[]" # JSON string
    suggested_actions: str = "[]"  # JSON string
    capa_recommendations: str = "[]" # JSON string
    status: RegulatoryImpactStatus = RegulatoryImpactStatus.pending

class RegulatoryImpactCreate(RegulatoryImpactBase):
    update_id: int
    project_id: int

class RegulatoryImpactUpdate(BaseModel):
    impact_summary: Optional[str] = None
    impacted_areas: Optional[str] = None
    suggested_actions: Optional[str] = None
    status: Optional[RegulatoryImpactStatus] = None

class RegulatoryImpactOut(RegulatoryImpactBase):
    id: int
    update_id: int
    project_id: int
    created_at: datetime
    update: Optional[RegulatoryUpdateOut] = None
    project: Optional[dict] = None # Or use ProjectOut if imported, but dict avoids circular imports if schemas are separated

    class Config:
        from_attributes = True
