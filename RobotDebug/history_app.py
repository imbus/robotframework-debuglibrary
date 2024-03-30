from __future__ import annotations

import re

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.filters import Always, has_selection
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.output import ColorDepth

from RobotDebug.lexer import HEADER_MATCHER, RobotFrameworkLocalLexer


class BORDER:
    HORIZONTAL = "\u2501"
    VERTICAL = "\u2503"
    TOP_LEFT = "\u250f"
    TOP_RIGHT = "\u2513"
    BOTTOM_LEFT = "\u2517"
    BOTTOM_RIGHT = "\u251b"
    LIGHT_VERTICAL = "\u2502"


def bottom_toolbar():
    base = []
    base.extend(
        [
            ("class:bottom-toolbar-key", "F4: "),
            (
                "class:bottom-toolbar",
                "Close History    ",
            ),
            ("class:bottom-toolbar-key", "TAB: "),
            (
                "class:bottom-toolbar",
                "Switch Focus    ",
            ),
            ("class:bottom-toolbar-key", "CTRL+C: "),
            (
                "class:bottom-toolbar",
                "Copy Selection    ",
            ),
        ]
    )
    return base


def run_history(context):
    buffer1 = Buffer()
    buffer2 = Buffer()
    his: FileHistory = context.history
    history = get_history_content(his)
    kw_history = get_history_content(his, False)
    buffer1.text = "\n".join(history)
    buffer1.cursor_position = len(buffer1.text)
    buffer1.read_only = Always()
    window1 = Window(
        content=BufferControl(buffer=buffer1, lexer=PygmentsLexer(RobotFrameworkLocalLexer))
    )
    vsplits = [
        window1,
        Window(
            width=Dimension.exact(1),
            char=BORDER.LIGHT_VERTICAL,
            style="class:separator",
        ),
    ]
    if kw_history:
        buffer2.text = f"\n#{BORDER.HORIZONTAL*35}\n".join(kw_history)
        buffer2.cursor_position = len(buffer2.text)
        buffer2.read_only = Always()
        window2 = Window(
            content=BufferControl(buffer=buffer2, lexer=PygmentsLexer(RobotFrameworkLocalLexer))
        )
        vsplits.append(window2)

    root_container = HSplit(
        [
            VSplit(
                vsplits,
                window_too_small=window1,
            ),
            Window(content=FormattedTextControl(bottom_toolbar()), style="bg:#333333"),
        ]
    )

    layout = Layout(root_container)

    def create_keybindings(ctx):
        kb = KeyBindings()

        @kb.add("c-q")
        @kb.add("escape")
        @kb.add("f4")
        def exit_(event):
            event.app.exit()

        @kb.add("tab")
        def tab(event):
            event.app.layout.focus_next()

        @kb.add("c-insert", filter=has_selection)
        @kb.add("c-c", filter=has_selection)
        def _(event):
            b: Buffer = event.app.current_buffer
            cpy = b.copy_selection()
            event.app.clipboard.set_data(cpy)

        return kb

    app = Application(
        clipboard=PyperclipClipboard(),
        color_depth=ColorDepth.DEPTH_24_BIT,
        cursor=CursorShape.BLINKING_BEAM,
        full_screen=True,
        include_default_pygments_style=False,
        key_bindings=create_keybindings(context),
        layout=layout,
        mouse_support=True,
        style=context.prompt_style,
    )
    app.run()


def get_history_content(his, pure_commands: bool = True):
    return list(
        reversed(
            [
                e
                for e in dict.fromkeys(
                    reversed(
                        [
                            re.sub(r"(?:(?<![\n ])(?:[ \t]{2,}|\t))", " " * 4, v).strip()
                            for v in his.get_strings()
                        ]
                    )
                )
                if bool(HEADER_MATCHER.match(e)) != pure_commands
            ]
        )
    )
