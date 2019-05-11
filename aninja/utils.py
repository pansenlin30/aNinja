import time
import dateparser
TIME_TEMPLATE = '%a, %d-%b-%Y %H:%M:%S GMT'

def filter_attrs(time_format='number',
                 attrs=('name', 'value', 'domain', 'path', 'expires'),
                 **kwargs)->dict:
    """filters a dictionary with expected attributes and expected time format
    for the expires attribute.

    Args:
        time_format: 'string' or 'number' or 'original'
        attrs: needed key for pairs
        kwargs: a key-value pairs for a cookie
    """
    result = {}
    for attr in attrs:
        if attr in kwargs:
            result[attr] = kwargs[attr]
            if attr == 'expires':
                result[attr] = format_expires(
                    kwargs[attr], time_format=time_format)
    return result


def format_expires(raw, time_format='number'):
    formatter = {
        'number': expires_to_number,
        'string': expires_to_str,
        'original': lambda x: x
    }
    return formatter[time_format](raw)


def expires_to_number(raw):
    if raw == -1:
        return None
    else:
        return _parse_expires_to_timestamp(raw)


def expires_to_str(raw, template=TIME_TEMPLATE):
    ts = _parse_expires_to_timestamp(raw)
    return time.strftime(template, time.gmtime(ts))


def _parse_expires_to_timestamp(raw):
    if isinstance(raw, str):
        dt = dateparser.parse(raw)
        return dt.timestamp()
    elif isinstance(raw, (int, float)):
        return raw
    else:
        raise TypeError('Need a valid expires time.')