# Importing all models here ensures SQLAlchemy's metadata is fully populated
# before create_all() or Alembic runs. Any new model must be added here.
from app.models import appointment, blocked_slot, customer, user  # noqa: F401
