from __future__ import annotations

import functools
import hashlib
import re
from dataclasses import dataclass

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

SCRIPT_FILENAME = "_appendix-{hash}.js"
SCRIPT_HTML_RE = re.compile(
    r"""<script\s+src=("|')_appendix-(.*?).js("|')></script>""",
    re.DOTALL | re.IGNORECASE,
)
SCRIPT_HTML = '<script src="{script_filename}"></script>'
CSS_FILENAME = "_appendix-{hash}.css"
CSS_IMPORT = '@import url("{css_filename}");'
CSS_IMPORT_RE = re.compile(
    r"""@import url\(("|')_appendix-(.*?).css("|')\);""",
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class AppendixFiles:
    script_filename: str
    css_filename: str


LIGHTBOX_CSS_IMAGE_REF_RE = re.compile(r"url\(\.\./images/([^.]*?\..*?)\)")


def add_vendored_libs_to_media_dir(col: Collection) -> dict[str, str]:
    def replace_css_image_ref(match: re.Match[str], mapping: dict[str, str]) -> str:
        return f"url({mapping[match.group(1)]})"

    mapping: dict[str, str] = {}
    dirs = (
        consts.dir / "web" / "vendor" / "lightbox2" / "images",
        consts.dir / "web" / "vendor" / "lightbox2" / "css",
        consts.dir / "web" / "vendor" / "lightbox2" / "js",
    )
    for dir_path in dirs:
        for path in dir_path.iterdir():
            if path.name == "lightbox.min.css":
                css = path.read_text(encoding="utf-8")
                css = LIGHTBOX_CSS_IMAGE_REF_RE.sub(
                    functools.partial(replace_css_image_ref, mapping=mapping), css
                )
                renamed_filename = col.media.write_data(path.name, css.encode())
            else:
                renamed_filename = col.media.add_file(str(path))
            mapping[path.name] = renamed_filename

    return mapping


def build_assets(col: Collection) -> AppendixFiles:
    script_path = consts.dir / "assets" / "_appendix.js"
    css_path = consts.dir / "assets" / "_appendix.css"
    vendor_assets = add_vendored_libs_to_media_dir(col)
    script_contents = script_path.read_bytes()
    script_contents = script_contents.replace(
        b"lightbox-plus-jquery.min.js",
        vendor_assets["lightbox-plus-jquery.min.js"].encode(),
    )
    hasher = hashlib.sha1(script_contents)
    (media_dir, _) = media_paths_from_col_path(col.path)
    script_filename = SCRIPT_FILENAME.format(hash=hasher.hexdigest())
    with open(os.path.join(media_dir, script_filename), "wb") as f:
        f.write(script_contents)
    css_contents = css_path.read_bytes()
    css_contents = css_contents.replace(
        b"lightbox.min.css", vendor_assets["lightbox.min.css"].encode()
    )
    hasher = hashlib.sha1(css_contents)
    css_filename = CSS_FILENAME.format(hash=hasher.hexdigest())
    with open(os.path.join(media_dir, css_filename), "wb") as f:
        f.write(css_contents)

    return AppendixFiles(script_filename=script_filename, css_filename=css_filename)


def notetype_has_assets(notetype: NotetypeDict) -> Qt.CheckState:
    templates = notetype["tmpls"]
    has_script = 0
    if CSS_IMPORT_RE.search(notetype["css"]):
        has_script += len(templates)
    for template in templates:
        for side in ["qfmt", "afmt"]:
            html: str = template[side]
            if SCRIPT_HTML_RE.search(html):
                has_script += 1

    value: Qt.CheckState
    if has_script == 3 * len(templates):
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
    filenames: AppendixFiles,
) -> None:
    templates = notetype["tmpls"]
    for template in templates:
        for side in ["qfmt", "afmt"]:
            html: str = template[side]
            script_html = SCRIPT_HTML.format(script_filename=filenames.script_filename)
            if SCRIPT_HTML_RE.search(html):
                html = SCRIPT_HTML_RE.sub(script_html, html)
            else:
                # FIXME: excessive newlines after frequent updates
                html += f"\n\n{script_html}"
            template[side] = html

        css = notetype["css"]
        css_import = CSS_IMPORT.format(css_filename=filenames.css_filename)
        if CSS_IMPORT_RE.search(css):
            css = CSS_IMPORT_RE.sub(css_import, css)
        else:
            css = f"{css_import}\n\n{css}"
        notetype["css"] = css


def remove_assets_from_notetype(notetype: NotetypeDict) -> bool:
    changed = False
    templates = notetype["tmpls"]
    for template in templates:
        for side in ["qfmt", "afmt"]:
            if SCRIPT_HTML_RE.search(template[side]):
                template[side] = SCRIPT_HTML_RE.sub("", template[side])
                changed = True
    if CSS_IMPORT_RE.search(notetype["css"]):
        notetype["css"] = CSS_IMPORT_RE.sub("", notetype["css"])
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
            filenames = build_assets(col)
            updated_notetypes: list[NotetypeDict] = []
            for name, checked in notetype_names_states:
                notetype = col.models.by_name(name)
                changed = False
                if checked:
                    add_assets_to_notetype(notetype, filenames)
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
