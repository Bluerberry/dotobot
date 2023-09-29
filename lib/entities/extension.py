
from pony.orm.core import Required
from .database import db

class Extension(db.Entity):
    name = Required(str, unique=True)
    active = Required(bool)


