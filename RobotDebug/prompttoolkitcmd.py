import cmd
import re
from pathlib import Path

from prompt_toolkit.application import get_app
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.filters import Condition, has_completions, has_selection
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.shortcuts import CompleteStyle, prompt

from . import RobotDebug
from .globals import StepMode
from .history_app import run_history
from .lexer import HEADER_MATCHER, RobotFrameworkLocalLexer


def listener():
    from . import Listener

    return Listener.instance


def dbg_cmd():
    return listener().library.debug_cmd


def exec_step(step_mode: StepMode):
    lstnr = listener()
    lstnr.step_mode = step_mode
    lstnr.library.debug_cmd.do_continue(None)


kb = KeyBindings()


@kb.add("c-space")
def _(event):
    """
    Start auto completion. If the menu is showing already, select the next
    completion.
    """
    b: Buffer = event.app.current_buffer
    if b.complete_state:
        b.complete_next()
    else:
        b.start_completion(select_first=False)


@kb.add("escape", filter=has_completions)
def _(event):
    """
    Closes auto completion.
    """
    b: Buffer = event.app.current_buffer
    b.cancel_completion()


@kb.add("escape", filter=~has_completions | ~has_selection)
def _(event):
    b: Buffer = event.app.current_buffer
    b.reset()


@kb.add("tab")
def _(event):
    """
    Accepts completion.
    """
    b: Buffer = event.app.current_buffer
    if b.complete_state:
        completion = b.complete_state.current_completion
        if completion:
            b.apply_completion(completion)
        else:
            b.cancel_completion()
    else:
        b.insert_text("    ")


@kb.add("enter")
def _(event):
    """
    Closes auto completion.
    """
    b: Buffer = event.app.current_buffer
    if b.complete_state:
        completion = b.complete_state.current_completion
        if completion:
            b.apply_completion(completion)
        else:
            b.cancel_completion()
    elif b.cursor_position == len(b.text) and re.fullmatch(r".*\n", b.text, re.DOTALL):
        b.validate_and_handle()
    elif (
        HEADER_MATCHER.match(b.text)
        or re.fullmatch(r"(FOR|IF|WHILE|TRY).*", b.text.strip())
        or re.search(r"\n", b.text)
    ):
        b.newline(False)
    else:
        b.validate_and_handle()


@Condition
def has_line_break():
    b = get_app().current_buffer
    return not re.search(r"\n", b.text)


@kb.add("s-down", filter=has_line_break)
@kb.add("c-down", filter=has_line_break)
def _(event):
    b: Buffer = event.app.current_buffer
    b.newline()


@kb.add("c-insert", filter=has_selection)
@kb.add("c-c", filter=has_selection)
def _(event):
    b: Buffer = event.app.current_buffer
    get_app().clipboard.set_data(b.copy_selection())


@kb.add("c-x", filter=has_selection)
def _(event):
    b: Buffer = event.app.current_buffer
    get_app().clipboard.set_data(b.cut_selection())


@kb.add("c-insert")
@kb.add("c-v")
def _(event):
    b: Buffer = event.app.current_buffer
    data = get_app().clipboard.get_data()
    b.paste_clipboard_data(data)


@kb.add("c-z")
def _(event):
    b: Buffer = event.app.current_buffer
    b.undo()


@kb.add("c-y")
def _(event):
    b: Buffer = event.app.current_buffer
    b.redo()


@kb.add("c-a")
def _(event):
    b: Buffer = event.app.current_buffer
    b.cursor_position = 0
    b.start_selection()
    b.cursor_position = len(b.text)


@kb.add("c-e")
def _(event):
    b: Buffer = event.app.current_buffer
    b.cursor_position = len(b.text)
    b.start_selection()
    b.cursor_position = 0


@kb.add("left", filter=has_selection)
@kb.add("right", filter=has_selection)
@kb.add("up", filter=has_selection)
@kb.add("down", filter=has_selection)
@kb.add("escape", filter=has_selection)
def _(event):
    b: Buffer = event.app.current_buffer
    b.exit_selection()


@kb.add("[")
def _(event):
    b = event.current_buffer
    b.insert_text("[")
    b.insert_text("]", move_cursor=False)


@kb.add("f8")
def _(event):
    b = event.current_buffer
    b.text = ""
    exec_step(StepMode.OVER)
    b.validate_and_handle()


@kb.add("f7")
def _(event):
    b = event.current_buffer
    b.text = ""
    exec_step(StepMode.INTO)
    b.validate_and_handle()


@kb.add("f9")
def _(event):
    b = event.current_buffer
    b.text = ""
    exec_step(StepMode.OUT)
    b.validate_and_handle()


@kb.add("f10")
def _(event):
    b = event.current_buffer
    b.text = ""
    exec_step(StepMode.CONTINUE)
    b.validate_and_handle()


@kb.add("s-tab")
def _(event):
    b = event.current_buffer
    b.text = ""
    exec_step(StepMode.STOP)
    b.validate_and_handle()


@kb.add("f12")
def _(event):
    b = event.current_buffer
    b.text = ""
    dbg_cmd().toggle_mouse()
    b.validate_and_handle()


@kb.add("f4")
def _(event):
    b = event.current_buffer
    b.text = "history"
    b.validate_and_handle()


@kb.add("f5")
def _(event):
    b = event.current_buffer
    b.text = ""
    dbg_cmd().toggle_live_completion()
    b.validate_and_handle()


class BaseCmd(cmd.Cmd):
    """Basic REPL tool."""

    prompt = "> "
    repeat_last_nonempty_command = False

    def emptyline(self):
        """Do not repeat the last command if input empty unless forced to."""
        if self.repeat_last_nonempty_command:
            return super().emptyline()
        return None

    def do_exit(self, arg):
        """Exit the interpreter. You can also use the Ctrl-D shortcut."""
        return True

    do_EOF = do_exit

    def get_cmd_names(self):
        """Get all command names of CMD shell."""
        pre = "do_"
        cut = len(pre)
        return [_[cut:] for _ in self.get_names() if _.startswith(pre)]

    def get_help_string(self, command_name):
        """Get help document of command."""
        func = getattr(self, f"do_{command_name}", None)
        if not func:
            return ""
        return func.__doc__

    def get_helps(self):
        """Get all help documents of commands."""
        return [(name, self.get_help_string(name) or name) for name in self.get_cmd_names()]

    def get_completer(self):
        """Get completer instance."""

    def pre_loop_iter(self):
        """Excute before every loop iteration."""

    def _get_input(self):
        if self.cmdqueue:
            return self.cmdqueue.pop(0)
        try:
            return self.get_input()
        except KeyboardInterrupt:
            return None

    def loop_once(self):
        self.pre_loop_iter()
        line = self._get_input()
        if line is None:
            return None

        if line in ["exit", "EOF"]:
            line = "EOF"
            return True

        line = self.precmd(line)
        stop = self.onecmd(line)
        return self.postcmd(stop, line)

        # do not run 'EOF' command to avoid override 'lastcmd'

    def cmdloop(self, intro=None):
        """Better command loop.

        override default cmdloop method
        """
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(self.intro)
            self.stdout.write("\n")

        self.preloop()

        stop = None
        while not stop:
            stop = self.loop_once()

        self.postloop()

    def get_input(self):
        return input(prompt=self.prompt)


class PrivateHistory(FileHistory):
    def append_string(self, string: str):
        """Append string to history file."""
        if string.startswith("_"):
            return
        super().append_string(string)


class PromptToolkitCmd(BaseCmd):
    """CMD shell using prompt-toolkit."""

    get_prompt_tokens = None
    prompt_style = None
    intro = """\
iRobot can interpret single or multiple keyword calls,
as well as FOR, IF, WHILE, TRY
and resource file syntax like *** Keywords*** or *** Variables ***.

Type "help" for more information.\
"""

    def __init__(self, library, history_path=""):
        super().__init__()
        self.library: RobotDebug = library
        self.history = PrivateHistory(str(Path(history_path).expanduser()))
        self.toolbar_token_tuple = ("", None, None)
        self.mouse_support = True
        self.complete_while_typing = False

    def do_history(self, arg):
        """Run app."""
        run_history(self)

    def toggle_live_completion(self):
        """Toggle live completion."""
        self.complete_while_typing = not self.complete_while_typing

    def toggle_mouse(self):
        """Toggle mouse support."""
        self.mouse_support = not self.mouse_support

    def prompt_continuation(self, width, line_number, is_soft_wrap):
        return " " * width

    def get_rprompt_text(self):
        return [("class:pygments.comment", "rprompt")]

    def set_toolbar_key(self, statement_type, token, cursor_pos):
        self.toolbar_token_tuple = statement_type, token, cursor_pos

    def postcmd(self, stop, line):
        """Hook method executed just after a command dispatch is finished."""
        self.toolbar_token_tuple = ("", None, None)
        return stop

    def bottom_toolbar(self):
        base = []
        if not self.library.is_repl:
            base.extend(
                [
                    ("class:bottom-toolbar-key", "F7: "),
                    ("class:bottom-toolbar", "INTO    "),
                    ("class:bottom-toolbar-key", "F8: "),
                    ("class:bottom-toolbar", "OVER    "),
                    ("class:bottom-toolbar-key", "F9: "),
                    ("class:bottom-toolbar", "OUT    "),
                    ("class:bottom-toolbar-key", "F10: "),
                    ("class:bottom-toolbar", "CONTINUE    "),
                    ("class:bottom-toolbar-key", "Shift+Tab: "),
                    ("class:bottom-toolbar", "DETACH    "),
                ]
            )
        base.extend(
            [
                ("class:bottom-toolbar-key", "F4: "),
                (
                    "class:bottom-toolbar",
                    "Open History    ",
                ),
                ("class:bottom-toolbar-key", "F5: "),
                (
                    "class:bottom-toolbar",
                    f"Toggle Live Completion ({'ON' if self.complete_while_typing else 'OFF'})    ",
                ),
                ("class:bottom-toolbar-key", "F12: "),
                (
                    "class:bottom-toolbar",
                    f"Toggle Mouse ({'ON' if self.mouse_support else 'OFF'})    ",
                ),
            ]
        )
        ##   UNCOMMEND FOR DEBUGGING
        # if self.toolbar_token_tuple:
        #     base.extend(
        #         [
        #             ("class:bottom-toolbar-key", "STATEMENT: "),
        #             ("class:bottom-toolbar", f"{self.toolbar_token_tuple[0]}    "),
        #             ("class:bottom-toolbar-key", "value: "),
        #             (
        #                 "class:bottom-toolbar",
        #                 f"{self.toolbar_token_tuple[1].value if self.toolbar_token_tuple[1] else ''}    ",
        #             ),
        #             ("class:bottom-toolbar-key", "TOKEN: "),
        #             (
        #                 "class:bottom-toolbar",
        #                 f"{self.toolbar_token_tuple[1].type if self.toolbar_token_tuple[1] else ''}    ",
        #             ),
        #             ("class:bottom-toolbar-key", "TOKEN: "),
        #             (
        #                 "class:bottom-toolbar",
        #                 f"{self.toolbar_token_tuple[2] if self.toolbar_token_tuple[2] else ''}    ",
        #             ),
        #         ]
        #     )
        return base

    def get_auto_suggester(self):
        return AutoSuggestFromHistory()

    def get_input(self):
        kwargs = {}
        if self.get_prompt_tokens:
            kwargs["style"] = self.prompt_style
            prompt_str = self.get_prompt_tokens(self.prompt)
        else:
            prompt_str = self.prompt
        try:
            line = prompt(
                auto_suggest=self.get_auto_suggester(),
                bottom_toolbar=self.bottom_toolbar,
                clipboard=PyperclipClipboard(),
                color_depth=ColorDepth.DEPTH_24_BIT,
                completer=self.get_completer(),
                complete_style=CompleteStyle.COLUMN,
                complete_while_typing=self.complete_while_typing,
                cursor=CursorShape.BLINKING_BEAM,
                enable_history_search=not self.complete_while_typing,
                history=self.history,
                include_default_pygments_style=False,
                key_bindings=kb,
                lexer=PygmentsLexer(RobotFrameworkLocalLexer),
                message=prompt_str,
                mouse_support=self.mouse_support,
                prompt_continuation=self.prompt_continuation,
                rprompt=self.get_rprompt_text(),
                **kwargs,
            )
        except EOFError:
            line = "EOF"
        return line
