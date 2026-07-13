from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import PlvPrice
from app.schemas import PlvPriceResponse, PlvPriceCreate, PlvPriceUpdate
from app.auth import get_current_user
from app.models import User

public_router = APIRouter(prefix="/public/plv-prices", tags=["public-plv-prices"])
admin_router = APIRouter(prefix="/admin/plv-prices", tags=["admin-plv-prices"])

# Prix par défaut si la table est vide (d'après les tarifs Sodigaz)
DEFAULT_PRICES = [
    {"bottle_label": "2.75 KG", "bottle_size_kg": 2.75, "price_fcfa": 770,  "city": "ALL"},
    {"bottle_label": "6 KG",    "bottle_size_kg": 6.0,  "price_fcfa": 1679, "city": "ALL"},
    {"bottle_label": "12.5 KG", "bottle_size_kg": 12.5, "price_fcfa": 4835, "city": "ALL"},
    {"bottle_label": "10.8 KG", "bottle_size_kg": 10.8, "price_fcfa": 4177, "city": "ALL"},
    {"bottle_label": "38 KG",   "bottle_size_kg": 38.0, "price_fcfa": 32212,"city": "ALL"},
    {"bottle_label": "55 KG",   "bottle_size_kg": 55.0, "price_fcfa": 46623,"city": "ALL"},
]


def _seed_defaults_if_empty(db: Session):
    """Si la table est vide, insère les tarifs par défaut."""
    count = db.query(PlvPrice).count()
    if count == 0:
        for p in DEFAULT_PRICES:
            db.add(PlvPrice(**p))
        db.commit()


# ── PUBLIC ENDPOINT ────────────────────────────────────────────────────────

@public_router.get("", response_model=List[PlvPriceResponse])
def get_public_plv_prices(
    city: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retourne tous les tarifs PLV actifs.
    Utilisé par l'application mobile PLV Collecte.
    Si la table est vide, sème les prix par défaut automatiquement.
    """
    _seed_defaults_if_empty(db)

    q = db.query(PlvPrice).filter(PlvPrice.is_active == True)
    if city:
        # Inclure les tarifs pour cette ville spécifique ET les tarifs "ALL"
        q = q.filter(
            (PlvPrice.city == city) | (PlvPrice.city == "ALL")
        )
    return q.order_by(PlvPrice.bottle_size_kg).all()


# ── ADMIN ENDPOINTS ───────────────────────────────────────────────────────

@admin_router.get("", response_model=List[PlvPriceResponse])
def get_all_plv_prices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Liste complète des tarifs PLV (admin)."""
    _seed_defaults_if_empty(db)
    return db.query(PlvPrice).order_by(PlvPrice.city, PlvPrice.bottle_size_kg).all()


@admin_router.post("", response_model=PlvPriceResponse, status_code=status.HTTP_201_CREATED)
def create_plv_price(
    data: PlvPriceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau tarif PLV."""
    price = PlvPrice(**data.dict())
    db.add(price)
    db.commit()
    db.refresh(price)
    return price


@admin_router.put("/{price_id}", response_model=PlvPriceResponse)
def update_plv_price(
    price_id: int,
    data: PlvPriceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour un tarif PLV."""
    price = db.query(PlvPrice).filter(PlvPrice.id == price_id).first()
    if not price:
        raise HTTPException(status_code=404, detail="Tarif PLV non trouvé")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(price, key, value)

    db.commit()
    db.refresh(price)
    return price


@admin_router.delete("/{price_id}")
def delete_plv_price(
    price_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un tarif PLV."""
    price = db.query(PlvPrice).filter(PlvPrice.id == price_id).first()
    if not price:
        raise HTTPException(status_code=404, detail="Tarif PLV non trouvé")

    db.delete(price)
    db.commit()
    return {"message": f"Tarif '{price.bottle_label}' supprimé avec succès"}
