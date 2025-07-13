from __future__ import annotations

import json
import os
import re
import shutil
from re import Match

from anki.collection import Collection, OpChangesWithCount
from anki.media import media_paths_from_col_path
from aqt import mw
from aqt.editor import Editor
from aqt.operations import CollectionOp
from aqt.qt import (
    QDragEnterEvent,
    QDropEvent,
    QFileDialog,
    QInputDialog,
    QListWidgetItem,
    QMessageBox,
    Qt,
    QWidget,
    qconnect,
)
from aqt.utils import openFolder, showInfo, tooltip

from ..forms.pdf_selector import Ui_Dialog
from .dialog import Dialog


class PdfSelectorDialog(Dialog):
    def __init__(self, parent: QWidget, editor: Editor) -> None:
        self.editor = editor
        self.media_dir, _ = media_paths_from_col_path(mw.col.path)
        self.all_pdfs: list[str] = []
        self.filtered_pdfs: list[str] = []
        self.selected_pdf = None
        super().__init__(parent)
        self.load_pdfs()

    def setup_ui(self) -> None:
        super().setup_ui()
        self.form = Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle("PDF Selector")

        qconnect(self.form.searchLineEdit.textChanged, self.on_search_changed)
        qconnect(
            self.form.pdfListWidget.itemSelectionChanged, self.on_selection_changed
        )
        qconnect(self.form.pdfListWidget.itemDoubleClicked, self.on_pdf_double_clicked)
        qconnect(self.form.addNewPdfButton.clicked, self.on_add_new_pdf)
        qconnect(self.form.renamePdfButton.clicked, self.on_rename_pdf)
        qconnect(self.form.addAppendixButton.clicked, self.on_add_appendix)
        qconnect(self.form.cancelButton.clicked, self.reject)

        self.form.searchLineEdit.setFocus()

        self.setAcceptDrops(True)

        self.update_button_states()

    def load_pdfs(self) -> None:
        """Load all PDF files from the media directory."""
        self.all_pdfs = []
        for filename in os.listdir(self.media_dir):
            if filename.lower().endswith(".pdf"):
                self.all_pdfs.append(filename)

        self.all_pdfs.sort(key=str.lower)
        self.filtered_pdfs = self.all_pdfs.copy()
        self.update_pdf_list()

    def update_pdf_list(self) -> None:
        """Update the PDF list widget with filtered results."""
        self.form.pdfListWidget.clear()
        for pdf_name in self.filtered_pdfs:
            item = QListWidgetItem(pdf_name)
            item.setData(Qt.ItemDataRole.UserRole, pdf_name)
            self.form.pdfListWidget.addItem(item)

    def on_search_changed(self, text: str) -> None:
        """Filter PDFs based on search text."""
        if not text:
            self.filtered_pdfs = self.all_pdfs.copy()
        else:
            search_lower = text.lower()
            self.filtered_pdfs = [
                pdf for pdf in self.all_pdfs if search_lower in pdf.lower()
            ]
        self.update_pdf_list()

    def on_selection_changed(self) -> None:
        """Update selected PDF and button states when selection changes."""
        selected_items = self.form.pdfListWidget.selectedItems()
        if selected_items:
            self.selected_pdf = selected_items[0].data(Qt.ItemDataRole.UserRole)
        else:
            self.selected_pdf = None
        self.update_button_states()

    def update_button_states(self) -> None:
        """Enable/disable buttons based on current state."""
        has_selection = self.selected_pdf is not None
        self.form.renamePdfButton.setEnabled(has_selection)
        self.form.addAppendixButton.setEnabled(has_selection)

    def on_pdf_double_clicked(self, item: QListWidgetItem) -> None:
        """Open PDF when double-clicked."""
        pdf_name = item.data(Qt.ItemDataRole.UserRole)
        self.open_pdf(pdf_name)

    def open_pdf(self, pdf_name: str) -> None:
        pdf_path = os.path.join(self.media_dir, pdf_name)
        openFolder(pdf_path)

    def on_add_new_pdf(self) -> None:
        """Add a new PDF file from file explorer."""

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF file", "", "PDF files (*.pdf);;All files (*.*)"
        )

        if not file_path:
            return

        try:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.media_dir, filename)

            # Check if file already exists
            if os.path.exists(dest_path):
                reply = QMessageBox.question(
                    self,
                    "File exists",
                    f"A file named '{filename}' already exists. Replace it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            shutil.copy2(file_path, dest_path)
            self.load_pdfs()

            # Select the newly added PDF
            for i in range(self.form.pdfListWidget.count()):
                item = self.form.pdfListWidget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == filename:
                    self.form.pdfListWidget.setCurrentItem(item)
                    break

            tooltip(f"PDF '{filename}' added successfully")

        except Exception as e:
            showInfo(f"Error adding PDF: {str(e)}")

    def on_rename_pdf(self) -> None:
        """Rename the selected PDF and update all notes that reference it."""
        if not self.selected_pdf:
            return

        old_name = self.selected_pdf
        new_name, ok = QInputDialog.getText(
            self, "Rename PDF", "Enter new name:", text=old_name
        )

        if not ok or not new_name or new_name == old_name:
            return

        # Ensure .pdf extension
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"

        old_path = os.path.join(self.media_dir, old_name)
        new_path = os.path.join(self.media_dir, new_name)

        # Check if new name already exists
        if os.path.exists(new_path):
            showInfo(f"A file named '{new_name}' already exists")
            return

        try:
            # Rename the file
            os.rename(old_path, new_path)

            # Update all notes that reference this PDF
            self.update_notes_with_renamed_pdf(old_name, new_name)

            # Reload PDF list
            self.load_pdfs()

            # Select the renamed PDF
            for i in range(self.form.pdfListWidget.count()):
                item = self.form.pdfListWidget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == new_name:
                    self.form.pdfListWidget.setCurrentItem(item)
                    break

            tooltip(f"PDF renamed from '{old_name}' to '{new_name}'")

        except Exception as e:
            showInfo(f"Error renaming PDF: {str(e)}")

    def update_notes_with_renamed_pdf(self, old_name: str, new_name: str) -> None:
        """Update all notes that reference the renamed PDF."""

        def op(col: Collection) -> OpChangesWithCount:
            # Escape special regex characters in filename for safe regex matching
            escaped_old_name = re.escape(old_name)

            # Search for notes containing href or src to the old PDF name
            # with optional page parameter
            # Matches both: href="filename.pdf" and href="filename.pdf?page=123"
            # Also matches: src="filename.pdf"
            search_pattern = (
                rf'''"re:(href|src)=[\"']?{escaped_old_name}(\?page=\\d+)?[\"']?"'''
            )
            note_ids = col.find_notes(search_pattern)
            updated_notes = []

            for note_id in note_ids:
                note = col.get_note(note_id)
                updated = False

                for i, field in enumerate(note.fields):
                    # Use regex to find and replace href references
                    # with optional page parameters
                    # Pattern matches: href="old_name" or href="old_name?page=123"
                    # (with single or double quotes)
                    href_pattern = rf'href=(["\']){re.escape(old_name)}(\?page=\d+)?\1'

                    def replace_href(match: Match[str]) -> str:
                        quote = match.group(1)  # Single or double quote
                        page_param = (
                            match.group(2) if match.group(2) else ""
                        )  # Page parameter if present
                        return f"href={quote}{new_name}{page_param}{quote}"

                    new_field = re.sub(href_pattern, replace_href, field)

                    # Also update src attributes in img tags
                    # Pattern matches: src="old_name" (with single or double quotes)
                    src_pattern = rf'src=(["\']){re.escape(old_name)}\1'

                    def replace_src(match: Match[str]) -> str:
                        quote = match.group(1)  # Single or double quote
                        return f"src={quote}{new_name}{quote}"

                    new_field = re.sub(src_pattern, replace_src, new_field)

                    if new_field != field:
                        note.fields[i] = new_field
                        updated = True

                if updated:
                    updated_notes.append(note)

            undo_entry = col.add_custom_undo_entry(
                f"Rename PDF: {old_name} → {new_name}"
            )
            for note in updated_notes:
                col.update_note(note)

            changes = col.merge_undo_entries(undo_entry)
            return OpChangesWithCount(changes=changes, count=len(updated_notes))

        def on_success(changes: OpChangesWithCount) -> None:
            if changes.count > 0:
                tooltip(f"Updated {changes.count} note(s) with new PDF name")

        CollectionOp(parent=self, op=op).success(on_success).run_in_background()

    def on_add_appendix(self) -> None:
        """Add the selected PDF as an appendix to the current note."""
        if not self.selected_pdf:
            return

        page_number = self.form.pageSpinBox.value()

        # Import the get_next_appendix_number function from editor module
        from ..editor import get_next_appendix_number  # noqa: PLC0415

        appendix_number = get_next_appendix_number(self.editor)

        # Create the appendix link
        if page_number > 0:
            link_text = f"🔗Appendix {appendix_number} (p.{page_number})"
        else:
            link_text = f"🔗Appendix {appendix_number}"
        href = self.selected_pdf + (f"?page={page_number}" if page_number > 0 else "")
        appendix_html = (
            f'<a href="{href}" class="appendix-link">'
            f"{link_text}"
            f'<img src="{self.selected_pdf}" style="display: none;"></a>'
        )

        mw.progress.single_shot(
            100,
            lambda: self.editor.web.eval(
                "document.execCommand('insertHTML', "
                f"false, {json.dumps(appendix_html)});"
            ),
        )

        self.accept()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event for PDF files."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith(".pdf") for url in urls):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event for PDF files."""
        if not self.media_dir:
            showInfo("Media directory not available")
            return

        urls = event.mimeData().urls()
        pdf_files = [
            url.toLocalFile()
            for url in urls
            if url.toLocalFile().lower().endswith(".pdf")
        ]

        if not pdf_files:
            return

        try:
            added_files = []
            for file_path in pdf_files:
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(self.media_dir, filename)

                    # Check if file already exists
                    if os.path.exists(dest_path):
                        reply = QMessageBox.question(
                            self,
                            "File exists",
                            f"A file named '{filename}' already exists. Replace it?",
                            QMessageBox.StandardButton.Yes
                            | QMessageBox.StandardButton.No,
                        )
                        if reply != QMessageBox.StandardButton.Yes:
                            continue

                    shutil.copy2(file_path, dest_path)
                    added_files.append(filename)

            if added_files:
                self.load_pdfs()

                # Select the first added PDF
                for i in range(self.form.pdfListWidget.count()):
                    item = self.form.pdfListWidget.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == added_files[0]:
                        self.form.pdfListWidget.setCurrentItem(item)
                        break

                count = len(added_files)
                tooltip(f"Added {count} PDF file(s) successfully")

        except Exception as e:
            showInfo(f"Error adding PDF files: {str(e)}")

        event.acceptProposedAction()
        count = len(added_files)
        tooltip(f"Added {count} PDF file(s) successfully")
