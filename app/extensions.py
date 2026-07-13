from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Inicie sesión para continuar."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id: str):
    from sqlalchemy.exc import OperationalError

    from app.models import User

    if not user_id or not user_id.isdigit():
        return None
    try:
        return db.session.get(User, int(user_id))
    except OperationalError:
        db.session.rollback()
        return None
