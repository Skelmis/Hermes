import datetime


def format_datetime(value: datetime.datetime, fmt="medium"):
    if fmt == "full":
        fmt = "%a %d %b %Y, %I:%M%p"
    elif fmt == "medium":
        fmt = "%I:%M%p, %d/%m/%Y"

    return value.strftime(fmt)
