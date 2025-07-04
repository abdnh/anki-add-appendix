from aqt import mw
from aqt.qt import QAction, QMenu, qconnect

from .patches import patch_certifi

patch_certifi()

# ruff: noqa: E402
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


def init() -> None:
    setup_error_handler()
    editor.init_hooks()
    web.init_hooks()
    add_menu()
    add_menu()
