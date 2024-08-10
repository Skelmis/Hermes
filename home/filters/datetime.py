import datetime


def format_datetime(value: datetime.datetime, fmt="medium"):
    if fmt == "full":
        fmt = "%I:%M%p, %a %d %b %Y"
    elif fmt == "medium":
        fmt = "%I:%M%p, %d/%m/%Y"

    return value.strftime(fmt)
