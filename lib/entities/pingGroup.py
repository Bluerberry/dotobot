
# External libraries
from pony.orm.core import Required, Optional, PrimaryKey, StrArray

# Local libraries
from .database import db


# ---------------------> External Classes


class PingGroup(db.Entity):
	id = PrimaryKey(int, auto=True)
	name = Required(str, unique=True)
	aliases = Optional(StrArray)
	steam_id = Optional(int, unique=True)
