from __future__ import annotations

import sys
from pathlib import Path

from robot.libraries.BuiltIn import BuiltIn

from .debugcmd import DebugCmd, ReplCmd, is_step_mode
from .globals import StepMode
from .styles import ERROR_STYLE, LOW_VISIBILITY_STYLE, print_output
from .version import VERSION

MUTING_KEYWORDS = [
    "Run Keyword And Ignore Error",
    "Run Keyword And Expect Error",
    "Run Keyword And Return Status",
    "Run Keyword And Warn On Failure",
    "Wait Until Keyword Succeeds",
]


class Listener:
    ROBOT_LISTENER_API_VERSION = 2
    instance: Listener = None

    def __init__(self, library: RobotDebug = None, is_library: bool = False):
        Listener.instance = self
        self.library = library or RobotDebug(cli_listener=self)
        self.source_files = {}
        self.new_error = True
        self.errormessage = {}
        self.mutings = []
        self.is_library = is_library
        self.keyword_layer = 0
        self.last_keyword_layer = 1
        self.step_mode: StepMode = StepMode.CONTINUE

    def start_keyword(self, name, attrs):
        if self.step_mode == StepMode.STOP:
            return
        self.keyword_layer += 1
        if attrs["kwname"] in MUTING_KEYWORDS:
            self.mutings.append(attrs["kwname"])

        path = attrs["source"]
        if path and Path(path).exists() and path not in self.source_files:
            self.source_files[path] = Path(path).open().readlines()  # noqa: SIM115
        lineno = attrs["lineno"]
        self.library.current_source_path = path
        self.library.current_source_line = lineno

        if (
            self.step_mode == StepMode.CONTINUE
            or (self.step_mode == StepMode.OVER and self.last_keyword_layer < self.keyword_layer)
            or (self.step_mode == StepMode.OUT and self.last_keyword_layer <= self.keyword_layer)
        ):
            return
        self.last_keyword_layer = self.keyword_layer

        print_output(
            "", f"{Path(path).relative_to(Path.cwd())}:{lineno}", style=LOW_VISIBILITY_STYLE
        )
        line = self.source_files[path][lineno - 1]
        print_output(f"{lineno} ->", line.rstrip())

        # callback debug interface
        self.library._debug(muted=True)

    def log_message(self, message):
        if message["level"] == "FAIL":
            self.errormessage = message

    def end_keyword(self, name, attrs):
        self.keyword_layer -= 1
        if attrs["status"] == "PASS":
            self.new_error = True
        if self.mutings and attrs["kwname"] == self.mutings[-1]:
            self.mutings.pop()
        if (
            attrs["status"] == "FAIL"
            and self.new_error
            and not self.mutings
            and not self.is_library
        ):
            print_output(
                self.errormessage.get("level", ""),
                self.errormessage.get("message", ""),
                style=ERROR_STYLE,
            )
            self.library.show_intro = True
            self.library._debug(muted=True)
            self.new_error = False
        if is_step_mode():
            for var_name in attrs.get("assign", []):
                val = BuiltIn().get_variable_value(var_name)
                print_output("#", f"{var_name} = {val!r}")


class RobotDebug:
    """Debug Library for RobotFramework."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = VERSION
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        self.cli_listener = kwargs.get("cli_listener", False)
        self.ROBOT_LIBRARY_LISTENER = (
            Listener(self, is_library=True)
            if not self.cli_listener and not Listener.instance
            else None
        )
        self.listener = self.cli_listener or Listener.instance or self.ROBOT_LIBRARY_LISTENER
        self.show_intro = True
        self.is_repl = kwargs.get("repl", False)
        self.debug_cmd = None
        self.current_source_line = 0
        self.current_source_path = ""

    def Library(self, name, *args):  # noqa: N802
        BuiltIn().import_library(name, *args)

    def Resource(self, path):  # noqa: N802
        BuiltIn().import_resource(path)

    def Variables(self, path, *args):  # noqa: N802
        BuiltIn().import_variables(path, *args)

    def debug(self):
        """Open a interactive shell, run any RobotFramework keywords.

        Keywords separated by two space or one tab, and Ctrl-D to exit.
        """
        # re-wire stdout so that we can use the cmd module and have readline
        # support
        return self._debug()

    def _debug(self, muted: bool = False):
        if self.listener.step_mode == StepMode.STOP:
            return
        old_stdout = sys.stdout
        sys.stdout = sys.__stdout__
        try:
            self.debug_cmd = ReplCmd(self) if self.is_repl else DebugCmd(self)
            if not is_step_mode() and not muted:
                print_output(">>>>>", "Enter interactive shell")
            if self.show_intro:
                self.show_intro = False
                if self.cli_listener:
                    print_output(
                        "File: ",
                        str(Path(self.current_source_path).relative_to(Path.cwd())) or "unknown",
                    )
                    self.debug_cmd.do_longlist("")
                    intro = "Execution interrupted by RobotDebug. Type 'help' for more information."
                else:
                    intro = None
            else:
                intro = ""
            self.debug_cmd.cmdloop(intro=intro)

            if not is_step_mode() and not muted:
                print_output("<<<<<", "Exit shell.")
        finally:
            # put stdout back where it was
            sys.stdout = old_stdout
