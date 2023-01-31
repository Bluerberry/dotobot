from pony.orm.core import Required
from .base import db


class Cog(db.Entity):
    cog_name = Required(str, unique=True)
    active = Required(bool)


