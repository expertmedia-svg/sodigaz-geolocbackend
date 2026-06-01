from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Auth Schemas
class UserLogin(BaseModel):
    username: str
    password: str

class UserChangePassword(BaseModel):
    current_password: str
    new_password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "user"

class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserAdminResetPassword(BaseModel):
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str


# Depot Schemas
class DepotCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = "Ouagadougou"
    quartier: Optional[str] = None
    capacity_6kg: Optional[int] = 0
    capacity_12kg: Optional[int] = 0
    plv_code: Optional[str] = None
    maps_url: Optional[str] = None
    itinerary_url: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = "Actif"
    comments: Optional[str] = None

class DepotUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    quartier: Optional[str] = None
    stock_6kg_plein: Optional[int] = None
    stock_12kg_plein: Optional[int] = None
    capacity_6kg: Optional[int] = None
    capacity_12kg: Optional[int] = None
    plv_code: Optional[str] = None
    maps_url: Optional[str] = None
    itinerary_url: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    comments: Optional[str] = None

class DepotResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    address: Optional[str]
    phone: Optional[str]
    city: str
    quartier: Optional[str]
    stock_6kg_plein: int
    stock_12kg_plein: int
    capacity_6kg: int
    capacity_12kg: int
    plv_code: Optional[str]
    maps_url: Optional[str]
    itinerary_url: Optional[str]
    description: Optional[str]
    is_active: bool
    status: str
    comments: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Stats & Sessions Schemas
class DepotMapFilters(BaseModel):
    cities: List[str]
    quartiers: List[str]

class DepotMapResponse(BaseModel):
    items: List[DepotResponse]
    filters: DepotMapFilters

class LocatorStatsResponse(BaseModel):
    total_depots: int
    today_usage: int
    active_sessions: int
    total_locations: int
    usage_trend: List[dict]
    top_depots: List[dict]

class LocatorSessionResponse(BaseModel):
    id: int
    depot_id: int
    depot_name: str
    username: Optional[str]
    is_active: bool
    created_at: datetime
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class LocationHistoryResponse(BaseModel):
    id: int
    depot_id: int
    depot_name: str
    latitude: float
    longitude: float
    accuracy: Optional[float]
    timestamp: datetime
    
    class Config:
        from_attributes = True
