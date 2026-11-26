"""Create (or promote) an administrator: python scripts/create_admin.py EMAIL USERNAME [PASSWORD]

The password is prompted for when omitted. An existing account with this email is promoted
to admin and re-activated; its password is left unchanged.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError
from sqlalchemy import select

from app.database import session_factory
from app.models import User
from app.schemas import UserRegister
from app.security import hash_password


def main(argv):
    if len(argv) not in (3, 4):
        raise SystemExit(__doc__)
    try:
        data = UserRegister(email=argv[1], username=argv[2],
                            password=argv[3] if len(argv) == 4 else getpass.getpass('Password: '))
    except ValidationError as error:
        raise SystemExit('; '.join(f"{e['loc'][-1]}: {e['msg']}" for e in error.errors())) from None
    with session_factory()() as db:
        user = db.scalar(select(User).where(User.email == data.email))
        if user is None:
            user = User(email=data.email, username=data.username, hashed_password=hash_password(data.password))
            db.add(user)
        user.role, user.is_active = 'admin', True
        db.commit()
        print(f'Administrator ready: {user.email} (id {user.id})')


if __name__ == '__main__':
    main(sys.argv)
