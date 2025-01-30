import json
import re
import urllib
from typing import Any, Callable, cast

from anki.hooks import wrap
from aqt import gui_hooks
from aqt.editor import Editor, pics
from bs4 import BeautifulSoup
from bs4.element import PageElement

from .config import config

appendix_mode_enabled = False


def update_appendix_mode_button_style(editor: Editor) -> None:
    editor.web.eval(
        """
(() => {
    const button = document.getElementById("toggle_appendix");
    const span = button.children[0];
    if(%(appendix_mode_enabled)s) {
        span.style.color = 'red';
    } else {
        span.style.removeProperty('color');
    }
})();
"""
        % dict(appendix_mode_enabled=json.dumps(appendix_mode_enabled))
    )


def on_toggle_appendix_mode(editor: Editor) -> None:
    global appendix_mode_enabled
    appendix_mode_enabled = not appendix_mode_enabled
    update_appendix_mode_button_style(editor)


def on_editor_did_init_buttons(buttons: list[str], editor: Editor) -> None:
    label_style = 'style="color: red"' if appendix_mode_enabled else ""
    tip = "Toggle Appendix Mode"
    if config["appendix_mode_shortcut"]:
        tip += f" ({config['appendix_mode_shortcut']})"
    button = editor.addButton(
        icon=None,
        cmd="appendix_mode",
        func=on_toggle_appendix_mode,
        tip=tip,
        label=f"<span {label_style}>A</span>",
        id="toggle_appendix",
        keys=config["appendix_mode_shortcut"],
    )
    buttons.append(button)


APPENDIX_TEXT_RE = re.compile(r"Appendix (\d+)")


def get_next_appendix_number(editor: Editor) -> int:
    note = editor.note
    max_number = 1
    for field in note.fields:
        soup = BeautifulSoup(field, "html.parser")
        for s in soup.find_all(string=APPENDIX_TEXT_RE):
            s = cast(PageElement, s)
            if not s.parent or s.parent.name != "a":
                continue

            match = APPENDIX_TEXT_RE.match(s)
            if match:
                number = int(match.group(1))
                if number >= max_number:
                    max_number = number + 1

    return max_number


def fname_to_link(self: Editor, fname: str, _old: Callable) -> str:
    if not appendix_mode_enabled:
        return _old(self, fname)
    ext = fname.split(".")[-1].lower()
    if ext not in pics and ext != "pdf":
        return _old(self, fname)
    name = urllib.parse.quote(fname.encode("utf8"))
    return f'<a href="{name}">Appendix {get_next_appendix_number(self)}</a>'


def url_to_link(*args: Any, **kwargs: Any) -> str:
    self: Editor = args[0]
    url: str = args[1]
    _old: Callable = kwargs.pop("_old")

    if appendix_mode_enabled and url.lower().endswith(".pdf"):
        return self.fnameToLink(self._retrieveURL(url))
    else:
        return _old(*args, **kwargs)


def init_hooks() -> None:
    gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
    Editor.fnameToLink = wrap(Editor.fnameToLink, fname_to_link, "around")  # type: ignore
    Editor.urlToLink = wrap(Editor.urlToLink, url_to_link, "around")  # type: ignore
