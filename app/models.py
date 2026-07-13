from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, event
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

def utc_now():
    return datetime.utcnow()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="user", nullable=False) # e.g. "admin", "user"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    sessions = relationship("LocatorSession", back_populates="user")


class Depot(Base):
    __tablename__ = "depots"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500), nullable=True)
    phone = Column(String(100), nullable=True)
    city = Column(String(100), default="Ouagadougou", nullable=False, index=True)
    quartier = Column(String(100), nullable=True, index=True)
    
    # Stock info
    stock_6kg_plein = Column(Integer, default=0, nullable=False)
    stock_12kg_plein = Column(Integer, default=0, nullable=False)
    capacity_6kg = Column(Integer, default=0, nullable=False)
    capacity_12kg = Column(Integer, default=0, nullable=False)
    
    plv_code = Column(String(50), unique=True, index=True, nullable=True)
    client_name = Column(String(255), nullable=True)
    maps_url = Column(String(500), nullable=True)
    itinerary_url = Column(String(500), nullable=True)
    description = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="Actif", nullable=False)
    comments = Column(String(1000), nullable=True)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    sessions = relationship("LocatorSession", back_populates="depot", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="depot", cascade="all, delete-orphan")


class LocatorSession(Base):
    __tablename__ = "locator_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    depot_id = Column(Integer, ForeignKey("depots.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    depot = relationship("Depot", back_populates="sessions")
    user = relationship("User", back_populates="sessions")


class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    depot_id = Column(Integer, ForeignKey("depots.id", ondelete="CASCADE"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)

    depot = relationship("Depot", back_populates="locations")


@event.listens_for(Depot, 'before_insert')
def auto_generate_urls_insert(mapper, connection, target):
    if target.maps_url in {'""', "''"}:
        target.maps_url = None
    if target.itinerary_url in {'""', "''"}:
        target.itinerary_url = None

    if target.latitude is not None and target.longitude is not None:
        if not target.maps_url:
            target.maps_url = f"https://www.google.com/maps?q={target.latitude},{target.longitude}"
        if not target.itinerary_url:
            target.itinerary_url = f"https://www.google.com/maps/dir/?api=1&destination={target.latitude},{target.longitude}"


@event.listens_for(Depot, 'before_update')
def auto_generate_urls_update(mapper, connection, target):
    if target.maps_url in {'""', "''"}:
        target.maps_url = None
    if target.itinerary_url in {'""', "''"}:
        target.itinerary_url = None

    if target.latitude is not None and target.longitude is not None:
        # If maps_url is empty, or is a standard google maps query url (which we should keep updated with coordinates)
        if not target.maps_url or "google.com/maps?q=" in target.maps_url or "maps.google.com/?q=" in target.maps_url:
            target.maps_url = f"https://www.google.com/maps?q={target.latitude},{target.longitude}"
        if not target.itinerary_url or "google.com/maps/dir/" in target.itinerary_url:
            target.itinerary_url = f"https://www.google.com/maps/dir/?api=1&destination={target.latitude},{target.longitude}"



class PlvPrice(Base):
    """Tarifs de recharge par format de bouteille et ville, configurables depuis l'admin."""
    __tablename__ = "plv_prices"

    id = Column(Integer, primary_key=True, index=True)
    bottle_label = Column(String(50), nullable=False)   # ex: "6 KG", "12.5 KG", "2.75 KG"
    bottle_size_kg = Column(Float, nullable=False)       # ex: 6.0, 12.5, 2.75
    price_fcfa = Column(Integer, nullable=False)         # prix recharge/bouteille en FCFA
    city = Column(String(100), default="ALL", nullable=False)  # "Ouagadougou", "Bobo-Dioulasso", "ALL"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
