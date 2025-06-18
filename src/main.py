import os
import sys

from aqt import mw
from aqt.qt import *

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from . import editor, web
from .consts import consts
from .errors import setup_error_handler
from .gui.notetypes import NotetypesDialog


def open_notetypes_dialog() -> None:
    dialog = NotetypesDialog(mw)
    dialog.open()


def add_menu() -> None:
    menu = QMenu(consts.name, mw)
    notetypes_action = QAction("Manage Notetypes", mw)
    menu.addAction(notetypes_action)
    mw.form.menuTools.addMenu(menu)
    qconnect(notetypes_action.triggered, open_notetypes_dialog)


setup_error_handler()
editor.init_hooks()
web.init_hooks()
add_menu()
