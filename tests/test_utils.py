from aninja.utils import format_expires


def test_format_expires():
    expires_str = "Thu Jun 06 2019 21:28:09 GMT+0800 (China Standard Time)"
    assert format_expires(expires_str, 'number')==1559827689
    assert format_expires(expires_str, 'string')=="Thu, 06-Jun-2019 13:28:09 GMT"

