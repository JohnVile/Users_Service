from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user_model import User


class UserRepository:

    def cria_usuario(self, db: Session, user_data):
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def busca_usuario_por_email(self, db: Session, email: str):
        return db.query(User).filter(User.email == email).first()

    def busca_usuario_por_id(self, db: Session, user_id: str):
        return db.query(User).filter(User.id == user_id).first()

    def lista_usuarios(
        self,
        db: Session,
        status: str | None = None,
        role: str | None = None,
        page: int = 0,
        size: int = 20,
    ):
        query = db.query(User)

        if status:
            query = query.filter(User.status == status)

        if role:
            query = query.filter(
                or_(
                    User.roles == role,
                    User.roles.like(f"{role},%"),
                    User.roles.like(f"%,{role},%"),
                    User.roles.like(f"%,{role}"),
                )
            )

        total = query.count()
        items = (
            query.order_by(User.created_at.desc())
            .offset(page * size)
            .limit(size)
            .all()
        )

        return items, total

    def atualiza_dados_do_usuario(self, db: Session, user, data):
        for key, value in data.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user
