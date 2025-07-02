from __future__ import annotations

from typing import cast

from aqt import gui_hooks
from aqt.browser.previewer import Previewer
from aqt.clayout import CardLayout
from aqt.qt import QWebEngineSettings
from aqt.reviewer import Reviewer
from aqt.webview import AnkiWebView, WebContent


def on_webview_will_set_content(
    web_content: WebContent, context: object | None
) -> None:
    if isinstance(context, Reviewer):
        web = cast(AnkiWebView, context.web)
    elif isinstance(context, CardLayout):
        web = context.preview_web
    elif isinstance(context, Previewer):
        web = context._web
    else:
        return
    web.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
    web.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)


def init_hooks() -> None:
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
