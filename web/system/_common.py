"""Small helpers shared by the web system operations."""

from random import Random


def int2b(x):
    """Convert a value to a boolean (``0``/``None`` become ``False``)."""
    return not (x is None or x == 0)


def random_str(randomlength=10):
    """Return a random alphanumeric string of the given length."""
    chars = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789"
    length = len(chars) - 1
    random = Random()
    return "".join(chars[random.randint(0, length)] for _ in range(randomlength))
