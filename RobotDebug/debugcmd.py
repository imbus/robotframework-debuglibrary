import difflib
import os
import time
from typing import List, Tuple

from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import merge_styles
from robot.api import logger
from robot.errors import ExecutionFailed, HandlerExecutionFailed
from robot.libraries.BuiltIn import BuiltIn
from robot.running import Keyword
from robot.running.context import _ExecutionContext
from robot.running.signalhandler import STOP_SIGNAL_MONITOR
from robot.variables import is_variable

from .cmdcompleter import CmdCompleter, KeywordAutoSuggestion
from .globals import IS_RF_7, context
from .lexer import HEADER_MATCHER
from .prompttoolkitcmd import PromptToolkitCmd
from .robotkeyword import (
    _get_assignments,
    _import_resource_from_string,
    find_keyword,
    get_keywords,
    get_lib_keywords,
    get_test_body_from_string,
)
from .robotlib import (
    get_libraries,
    get_libs,
    get_resources,
    match_libs,
)
from .sourcelines import (
    print_source_lines,
    print_test_case_lines,
)
from .styles import (
    BASE_STYLE,
    DEBUG_PROMPT_STYLE,
    _get_print_style,
    get_debug_prompt_tokens,
    get_pygments_styles,
    get_style_by_name,
    print_error,
    print_output,
    style_from_pygments_cls,
)

HISTORY_PATH = os.environ.get("RFDEBUG_HISTORY", "~/.rfdebug_history")


class ReplCmd(PromptToolkitCmd):
    """Interactive debug shell for robotframework."""

    prompt_style = DEBUG_PROMPT_STYLE

    def __init__(self, library):
        super().__init__(library, history_path=HISTORY_PATH)
        self.last_keyword_exec_time = 0
        self.listener = self.library.cli_listener or self.library.ROBOT_LIBRARY_LISTENER

    def do_continue(self, args):
        """Continue execution."""
        return self.do_exit(args)

    do_c = do_continue

    def get_prompt_tokens(self, prompt_text):
        return get_debug_prompt_tokens(prompt_text)

    def pre_loop_iter(self):
        """Reset robotframework before every loop iteration."""
        reset_robotframework_exception()

    def do_help(self, arg):
        """Show help message."""
        if not arg.strip():
            print_output(
                "",
                """\
Input Robotframework keywords, or commands listed below.
Use "libs" or "l" to see available libraries,
use "keywords" or "k" see the list of library keywords,
use CTRL+SPACE to autocomplete keywords.
Access https://github.com/imbus/robotframework-debug for more details.\
""",
            )
        super().do_help(arg)

    def get_completer(self):
        """Get completer instance specified for robotframework."""
        return CmdCompleter(get_libs(), get_keywords(), self.get_helps(), self)

    def get_auto_suggester(self):
        return KeywordAutoSuggestion(self.get_completer())

    def default(self, line):
        """Run RobotFramework keywords."""
        command = line.strip()

        self.run_robot_command(command)

    def run_robot_command(self, command):
        """Run command in robotframework environment."""
        if not command:
            return
        result = []
        try:
            result = run_command(self, command)
        except HandlerExecutionFailed as exc:
            print_error("! FAIL:", exc.message)
        except ExecutionFailed as exc:
            print_error("! Expression:", command if "\n" not in command else f"\n{command}")
            print_error("! Execution error:", str(exc))
        except Exception as exc:
            print_error("! Expression:", command)
            print_error("! Error:", repr(exc))
        if result:
            for head, message in result:
                print_output(head, message)

    def get_rprompt_text(self):
        """Get text for bottom toolbar."""
        if self.last_keyword_exec_time == 0:
            return None
        return [("class:pygments.comment", f"# ΔT: {self.last_keyword_exec_time:.3f}s")]

    def _print_lib_info(self, lib, with_source_path=False):
        print_output(f"   {lib.name}", lib.version if hasattr(lib, "version") else "")
        if lib.doc:
            doc = lib.doc.split("\n")[0]
            logger.console(f"       {doc}")
        if with_source_path:
            logger.console(f"       {lib.source}")

    def do_libs(self, args):
        """Print imported and builtin libraries, with source if `-s` specified."""
        print_output("<", "Imported libraries:")
        for lib in get_libraries():
            self._print_lib_info(lib, with_source_path="-s" in args)

    def do_res(self, args):
        """Print imported and builtin libraries, with source if `-s` specified."""
        print_output("<", "Imported resources:")
        for lib in get_resources():
            self._print_lib_info(lib, with_source_path="-s" in args)

    def do_keywords(self, args):
        """Print keywords of libraries, all or starts with <lib_name>.

        k(eywords) [<lib_name>]
        """
        lib_name = args
        matched = match_libs(lib_name)
        if not matched:
            print_error("< not found library", lib_name)
            return
        for lib in matched:
            if lib:
                print_output("< Keywords of library", lib.name)
                for keyword in get_lib_keywords(lib):
                    print_output(f"   {keyword.name}\t", keyword.shortdoc)

    do_k = do_keywords

    def do_docs(self, keyword_name):
        """Get keyword documentation for individual keywords.

        d(ocs) [<keyword_name>]
        """

        keywords = find_keyword(keyword_name)
        if not keywords:
            print_error("< not find keyword", keyword_name)
        elif len(keywords) == 1:
            logger.console(keywords[0].doc)
        else:
            print_error(
                f"< found {len(keywords)} keywords",
                ", ".join([k.name for k in keywords]),
            )

    do_d = do_docs

    def emptyline(self):
        """Repeat last nonempty command if in step mode."""
        self.repeat_last_nonempty_command = is_step_mode()
        return super().emptyline()

    def append_command(self, command):
        """Append a command to queue."""
        self.cmdqueue.append(command)

    def append_exit(self):
        """Append exit command to queue."""
        self.append_command("exit")

    def do_exit(self, args):
        """Exit debug shell."""
        set_step_mode(on=False)  # explicitly exit REPL will disable step mode
        self.append_exit()
        return super().do_exit(args)

    def onecmd(self, line):
        # restore last command acrossing different Cmd instances
        self.lastcmd = context.last_command
        stop = super().onecmd(line)
        context.last_command = self.lastcmd
        return stop

    def do_style(self, args):
        """Set style of output. Usage `style    <style_name>`. Call just `style` to list all styles."""
        styles = get_pygments_styles()
        if not args.strip():
            for style in styles:
                print_output(f"> {style}    ", style, _get_print_style(style))
            return
        style = difflib.get_close_matches(args.strip(), styles)[0]
        self.prompt_style = merge_styles(
            [BASE_STYLE, style_from_pygments_cls(get_style_by_name(style))]
        )
        print_output("Set style to:   ", style, _get_print_style(str(style)))

    def do_clear(self, args):
        """Clear screen."""
        clear()

    do_cls = do_clear


class DebugCmd(ReplCmd):
    def do_list(self, args):
        """List source code for the current file."""

        self.list_source(longlist=False)

    do_l = do_list

    def do_longlist(self, args=None):
        """List the whole source code for the current test case."""

        self.list_source(longlist=True)

    do_ll = do_longlist

    def list_source(self, longlist=False):
        """List source code."""
        # if not is_step_mode():
        #     print_output("i:", "Please run `step` or `next` command first.")
        #     return

        print_function = print_test_case_lines if longlist else print_source_lines
        print_function(
            self.prompt_style,
            self.library.current_source_path,
            self.library.current_source_line,
        )


def reset_robotframework_exception():
    """Resume RF after press ctrl+c during keyword running."""
    if STOP_SIGNAL_MONITOR._signal_count:
        STOP_SIGNAL_MONITOR._signal_count = 0
        STOP_SIGNAL_MONITOR._running_keyword = True
        logger.info("Reset last exception of DebugLibrary")


def set_step_mode(on=True):
    context.in_step_mode = on


def is_step_mode():
    return context.in_step_mode


def run_command(dbg_cmd, command: str) -> List[Tuple[str, str]]:
    """Run a command in robotframewrk environment."""
    dbg_cmd.last_keyword_exec_time = 0
    if not command:
        return []
    if is_variable(command):
        return [("#", f"{command} = {BuiltIn().get_variable_value(command)!r}")]
    ctx = BuiltIn()._get_context()
    # if command.startswith("***"):
    if HEADER_MATCHER.match(command):
        _import_resource_from_string(command)
        return [("i:", "Resource imported.")]
    test = get_test_body_from_string(command)
    if len(test.body) > 1:
        start = time.monotonic()
        for kw in test.body:
            run_keyword(kw, ctx)
        dbg_cmd.last_keyword_exec_time = time.monotonic() - start
        return_val = None
    else:
        kw = test.body[0]
        start = time.monotonic()
        return_val = run_keyword(kw, ctx)
        dbg_cmd.last_keyword_exec_time = time.monotonic() - start
    assign = set(_get_assignments(test))
    if not assign and return_val is not None:
        return [("<", repr(return_val))]
    if assign:
        output = []  # [("<", repr(return_val))] if return_val is not None else []
        for variable in assign:
            pure_var = variable.rstrip("=").strip()
            val = BuiltIn().get_variable_value(pure_var)
            output.append(("#", f"{pure_var} = {val!r}"))
        return output
    return []


def run_keyword(keyword: Keyword, context: _ExecutionContext):
    if IS_RF_7:
        test = context.test or context.suite
        return keyword.run(test, context)
    return keyword.run(context)
