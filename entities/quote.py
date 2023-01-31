from pony.orm.core import Required, PrimaryKey, Optional
from .base import db

class Quote(db.Entity):
    quote_id = Required(int)
    guild_id = Required(int)
    PrimaryKey(quote_id, guild_id)
    author = Required(str)
    quote = Required(str)
    author_discord_id = Optional(int)
