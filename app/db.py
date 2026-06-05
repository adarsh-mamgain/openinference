from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extras import RealDictCursor

from app.settings import SETTINGS


@contextmanager
def postgres_connection() -> Iterator[psycopg2.extensions.connection]:
    connection = psycopg2.connect(SETTINGS.database_url)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@contextmanager
def postgres_cursor() -> Iterator[RealDictCursor]:
    with postgres_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor
