
# External libraries
from pony.orm.core import Required, Optional, PrimaryKey

# Local libraries
from .database import db


# ---------------------> External Classes


class PingGroup(db.Entity):
	id = PrimaryKey(int, auto=True)
	name = Required(str, unique=True)
	steam_id = Optional(int, unique=True)
