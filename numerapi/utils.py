import dateutil.parser


def parse_datetime_string(s):
    if s is None:
        return None
    dt = dateutil.parser.parse(s)
    return dt
