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

    def busca_usuario_por_id(self, db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()

    def lista_todos_os_usuarios(self, db: Session):
        return db.query(User).all()

    def atualiza_dados_do_usuario(self, db: Session, user, data):
        for key, value in data.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user