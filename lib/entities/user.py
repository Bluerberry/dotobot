
# External libraries
from pony.orm.core import Required, PrimaryKey, Optional, IntArray

# Local libraries
from .database import db


# ---------------------> External Classes


class User(db.Entity):
	discord_id = Required(int, unique=True, size=64)
	steam_id = Optional(int, size=64)

	blacklisted_pings = Optional(IntArray)
	whitelisted_pings = Optional(IntArray)

class BannedUser(db.Entity):
	user_id = Required(int, size=64)
	guild_id = Required(int)
	PrimaryKey(user_id, guild_id)

	banned_roles = Optional(IntArray)
	nickname = Optional(str)
