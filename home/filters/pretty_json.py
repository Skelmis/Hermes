import orjson


def pretty_json(value: str) -> str:
    return orjson.dumps(orjson.loads(value), option=orjson.OPT_INDENT_2).decode("utf-8")
