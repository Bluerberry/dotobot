from pony.orm.core import Required, PrimaryKey, Optional
from .base import db


class Quote(db.Entity):
    quote_id = Required(int, size=64)
    guild_id = Required(int, size=64)
    PrimaryKey(quote_id, guild_id)
    author = Required(str)
    quote = Required(str)
    author_discord_id = Optional(int, size=64)

    def __str__(self) -> str:
        return f"{self.quote_id}: \"{self.quote}\" - {self.author}"
