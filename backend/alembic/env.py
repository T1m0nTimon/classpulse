from alembic import context
from sqlalchemy import DateTime

from classpulse import models  # noqa: F401 - registers tables
from classpulse.config import get_settings
from classpulse.db import Base, make_engine

config = context.config
url = config.get_main_option("sqlalchemy.url") or get_settings().database_url


def render_item(type_, obj, autogen_context):
    if type_ == "type" and isinstance(obj, models.UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run():
    engine = make_engine(url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata, render_item=render_item,
                          render_as_batch=url.startswith("sqlite"))
        with context.begin_transaction():
            context.run_migrations()


run()
