
# External libraries
from pony.orm.core import Required, PrimaryKey

# Local libraries
from .database import db


# ---------------------> External Classes


class Quote(db.Entity):
	guild_id = Required(int, size=64)
	quote_id = Required(int, size=64)
	PrimaryKey(quote_id, guild_id)

	author = Required(str)
	content = Required(str)

	def __str__(self) -> str:
		return f'{self.quote_id}) \"{self.content}\" - {self.author}'
