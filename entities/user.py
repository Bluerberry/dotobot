from pony.orm.core import Required, PrimaryKey, Optional, Set, StrArray, IntArray
from .base import db


class SteamUser(db.Entity):
    user_id = Required(int, unique=True)
    steam_id = Optional(int)

    blacklisted_games = Optional(StrArray)
    whitelisted_games = Optional(StrArray)


class BannedUser(db.Entity):
    user_id = Required(int)
    guild_id = Required(int)
    PrimaryKey(user_id, guild_id)

    banned_roles = Optional(IntArray)
    nickname = Optional(str)
