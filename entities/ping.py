from pony.orm.core import Required, Optional, PrimaryKey
from .base import db

class Ping(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str, unique=True)
    steam_id = Optional(int)
