from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..middleware import get_current_user
from ..models import User
from ..schemas import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/profile", response_model=UserOut)
def get_profile(user: User = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado."""
    return user


@router.put("/profile", response_model=UserOut)
def update_profile(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Actualiza el nombre del usuario autenticado."""
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    db.commit()
    db.refresh(user)
    return user