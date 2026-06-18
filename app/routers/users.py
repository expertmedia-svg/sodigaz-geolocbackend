from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserResponse, UserCreate, UserUpdate, UserAdminResetPassword
from app.auth import get_password_hash, require_admin

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """List all users (admin only)."""
    return db.query(User).order_by(User.created_at.desc()).all()

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Create a new user (admin only)."""
    # Check if username exists
    existing_username = db.query(User).filter(User.username == data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nom d'utilisateur est déjà pris."
        )
        
    # Check if email exists
    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'adresse email est déjà prise."
        )
        
    hashed_pwd = get_password_hash(data.password)
    new_user = User(
        email=data.email,
        username=data.username,
        hashed_password=hashed_pwd,
        full_name=data.full_name,
        role=data.role or "user",
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Update a user's details (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé."
        )
        
    # Check username unique
    if data.username and data.username != user.username:
        existing = db.query(User).filter(User.username == data.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nom d'utilisateur est déjà pris."
            )
        user.username = data.username
        
    # Check email unique
    if data.email and data.email != user.email:
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'adresse email est déjà prise."
            )
        user.email = data.email
        
    if data.full_name is not None:
        user.full_name = data.full_name
        
    if data.role is not None:
        # Prevent demoting oneself to avoid losing admin access
        if user.id == admin_user.id and data.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas retirer votre propre rôle d'administrateur."
            )
        user.role = data.role
        
    if data.is_active is not None:
        # Prevent disabling oneself
        if user.id == admin_user.id and not data.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas désactiver votre propre compte."
            )
        user.is_active = data.is_active
        
    db.commit()
    db.refresh(user)
    return user

@router.put("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    data: UserAdminResetPassword,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Reset a user's password (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé."
        )
        
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Mot de passe réinitialisé avec succès."}

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé."
        )
        
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas supprimer votre propre compte."
        )
        
    db.delete(user)
    db.commit()
    return {"message": "Utilisateur supprimé avec succès."}
