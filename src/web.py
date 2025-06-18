from __future__ import annotations

from aqt import gui_hooks
from aqt.qt import QWebEngineSettings
from aqt.reviewer import Reviewer
from aqt.webview import WebContent


def on_webview_will_set_content(
    web_content: WebContent, context: object | None
) -> None:
    if not isinstance(context, Reviewer):
        return
    context.web.settings().setAttribute(
        QWebEngineSettings.WebAttribute.PluginsEnabled, True
    )
    context.web.settings().setAttribute(
        QWebEngineSettings.WebAttribute.PdfViewerEnabled, True
    )


def init_hooks() -> None:
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
