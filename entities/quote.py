from pony.orm.core import Required
from .base import db


class Quote(db.entity):
    id = Required(int)
