from __future__ import annotations

import hashlib
import re

from anki.collection import Collection, OpChanges
from anki.media import media_paths_from_col_path
from anki.models import NotetypeDict
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import *
from aqt.qt import Qt
from aqt.utils import tooltip

from ..consts import consts
from ..forms.notetypes import Ui_Dialog
from .dialog import Dialog

SCRIPT_FILENAME = "_appendix-viewer-{hash}.js"
SCRIPT_HTML_RE = re.compile(
    r"""<script\s+src=("|')_appendix-(.*?).js("|')></script>""",
    re.DOTALL | re.IGNORECASE,
)
SCRIPT_HTML = '<script src="{script_filename}"></script>'


def build_script(col: Collection) -> str:
    script_path = consts.dir / "web" / "dist" / "_appendix-viewer.js"
    script_contents = script_path.read_bytes()
    hasher = hashlib.sha1(script_contents)
    (media_dir, _) = media_paths_from_col_path(col.path)
    script_filename = SCRIPT_FILENAME.format(hash=hasher.hexdigest())
    with open(os.path.join(media_dir, script_filename), "wb") as f:
        f.write(script_contents)

    return script_filename


def notetype_has_assets(notetype: NotetypeDict) -> Qt.CheckState:
    templates = notetype["tmpls"]
    has_script = 0
    for template in templates:
        for side in ["qfmt", "afmt"]:
            html: str = template[side]
            if SCRIPT_HTML_RE.search(html):
                has_script += 1

    value: Qt.CheckState
    if has_script == 2 * len(templates):
        value = Qt.CheckState.Checked
    elif has_script == 0:
        value = Qt.CheckState.Unchecked
    else:
        value = Qt.CheckState.PartiallyChecked
    return value


def get_notetypes_have_assets() -> dict[str, Qt.CheckState]:
    notetypes = mw.col.models.all()
    notetypes_have_script: dict[str, Qt.CheckState] = {}
    for notetype in notetypes:
        notetypes_have_script[notetype["name"]] = notetype_has_assets(notetype)
    return notetypes_have_script


def add_assets_to_notetype(
    notetype: NotetypeDict,
    script_filename: str,
) -> None:
    templates = notetype["tmpls"]
    for template in templates:
        for side in ["qfmt", "afmt"]:
            html: str = template[side]
            script_html = SCRIPT_HTML.format(script_filename=script_filename)
            if SCRIPT_HTML_RE.search(html):
                html = SCRIPT_HTML_RE.sub(script_html, html)
            else:
                # FIXME: excessive newlines after frequent updates
                html += f"\n\n{script_html}"
            template[side] = html


def remove_assets_from_notetype(notetype: NotetypeDict) -> bool:
    changed = False
    templates = notetype["tmpls"]
    for template in templates:
        for side in ["qfmt", "afmt"]:
            if SCRIPT_HTML_RE.search(template[side]):
                template[side] = SCRIPT_HTML_RE.sub("", template[side])
                changed = True

    return changed


def toggle_all_list_items(list_widget: QListWidget) -> None:
    all_checked = True
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        if item.checkState() != Qt.CheckState.Checked:
            all_checked = False
            break
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        item.setCheckState(
            Qt.CheckState.Checked if not all_checked else Qt.CheckState.Unchecked
        )


class NotetypesDialog(Dialog):
    def setup_ui(self) -> None:
        super().setup_ui()
        self.form = Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle(f"{consts.name} - Manage Notetypes")
        qconnect(self.form.cancel.clicked, self.reject)
        qconnect(self.form.save.clicked, self.accept)
        qconnect(self.form.toggle_all_notetypes.clicked, self.on_toggle_all)

        note_types = get_notetypes_have_assets()
        for note_type, state in note_types.items():
            item = QListWidgetItem(note_type)
            item.setCheckState(state)
            self.form.notetypes.addItem(item)

    def on_toggle_all(self) -> None:
        toggle_all_list_items(self.form.notetypes)

    def accept(self) -> None:
        self.save()
        super().accept()

    def save(self) -> None:
        notetype_names_states: list[tuple[str, bool]] = []
        for i in range(self.form.notetypes.count()):
            item = self.form.notetypes.item(i)
            notetype_names_states.append(
                (item.text(), item.checkState() == Qt.CheckState.Checked)
            )

        def op(col: Collection) -> OpChanges:
            script_filename = build_script(col)
            updated_notetypes: list[NotetypeDict] = []
            for name, checked in notetype_names_states:
                notetype = col.models.by_name(name)
                changed = False
                if checked:
                    add_assets_to_notetype(notetype, script_filename)
                    changed = True
                else:
                    changed = remove_assets_from_notetype(notetype)
                if changed:
                    updated_notetypes.append(notetype)

            undo_entry = col.add_custom_undo_entry("Appendix: Update Notetypes")
            for notetype in updated_notetypes:
                col.models.update_dict(notetype)
                # Merge to our custom undo entry before the undo queue fills up and Anki discards our entry
                if (col.undo_status().last_step - undo_entry) % 29 == 0:
                    col.merge_undo_entries(undo_entry)
            changes = col.merge_undo_entries(undo_entry)

            return changes

        def on_success(changes: OpChanges) -> None:
            tooltip("Notetypes updated")

        CollectionOp(parent=self, op=op).success(on_success).run_in_background()
