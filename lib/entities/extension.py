
# External libraries
from pony.orm.core import Required

# Local libraries
from .database import db


# ---------------------> External Classes


class Extension(db.Entity):
	name = Required(str, unique=True)
	active = Required(bool)


