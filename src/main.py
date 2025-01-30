import os
import sys

from aqt.qt import *

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from . import editor
from .errors import setup_error_handler

setup_error_handler()
editor.init_hooks()
