import sys
from io import StringIO

from biox import hello


def test_hello_prints_hello_world() -> None:
    # Capture stdout
    buf = StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        hello()
    finally:
        sys.stdout = old_stdout

    assert buf.getvalue().strip() == "Hello, World!"
