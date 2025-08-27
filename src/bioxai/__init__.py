"""BioXAI package."""

from .core import hello
from .logger.log import setup_logger

__all__ = ["hello", "__version__", "__author__", "__license__", "__url__"]
__version__ = "0.0.2"
__author__ = "Rahulk Brahma"
__license__ = "MIT"
__url__ = "https://github.com/takshan/bioxai"
__email__ = "rahu.brahma@uni-greifswald.de"

logger = setup_logger()
