import asyncpg


def default(obj):
    if isinstance(obj, asyncpg.pgproto.pgproto.UUID):
        return str(obj)

    raise TypeError
