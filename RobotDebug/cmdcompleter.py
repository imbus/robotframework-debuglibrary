import re
from typing import Optional, Union

from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from robot.libraries.BuiltIn import BuiltIn
from robot.parsing.parser.parser import _tokens_to_statements

from .globals import IS_RF_7, KEYWORD_SEP
from .lexer import get_robot_token, get_variable_token
from .prompttoolkitcmd import PromptToolkitCmd
from .robotkeyword import normalize_kw
from .styles import _get_style_completions

# def find_token_at_cursor(cursor_col, cursor_row, statement):
#     statement_type = None
#     for token in statement.tokens:
#         if token.type in ["KEYWORD", "IF", "FOR", "ELSE", "ELSE IF"]:
#             statement_type = token.type
#         if (
#             token.lineno == cursor_row + 1
#             and token.col_offset <= cursor_col <= token.end_col_offset
#         ):
#             return statement_type, token, cursor_col - token.col_offset
#     return None, None, None
#
#
# def find_statement_details_at_cursor(cursor_col, cursor_row, statements):
#     for statement in statements:
#         if not statement:
#             continue
#         if (
#             statement.lineno <= cursor_row + 1 <= statement.end_lineno
#             and statement.col_offset <= cursor_col <= statement.end_col_offset
#         ):
#             statement_type, token, cursor_pos = find_token_at_cursor(
#                 cursor_col, cursor_row, statement
#             )
#             if token:
#                 return statement, statement_type, token, cursor_pos
#     return None, None, None, None


class StatementInformation:
    def __init__(self, cursor_col, cursor_row, statements):
        self.cursor_col = cursor_col
        self.cursor_row = cursor_row
        self.statements = statements
        self.statement = None
        self.statement_type = None
        self.token = None
        self.previous_token = None
        self.cursor_pos = None
        self._find_statement_details_at_cursor()

    def _find_statement_details_at_cursor(self):
        for statement in self.statements:
            if not statement:
                continue
            if (
                statement.lineno <= self.cursor_row + 1 <= statement.end_lineno
                and statement.col_offset <= self.cursor_col <= statement.end_col_offset
            ):
                self.statement = statement
                self._find_token_at_cursor()
                return

    def _find_token_at_cursor(self):
        for token in self.statement.tokens:
            if token.type in [
                "KEYWORD",
                "IF",
                "FOR",
                "ELSE",
                "ELSE IF",
                "TRY",
                "WHILE",
                "VAR",
            ]:  # TODO: Commented to get all tokens in debug. lets see the impact
                self.statement_type = token.type
            if (
                token.lineno == self.cursor_row + 1
                and token.col_offset <= self.cursor_col <= token.end_col_offset
            ):
                self.token = token
                self.cursor_pos = self.cursor_col - token.col_offset
                return
            self.previous_token = token


class CmdCompleter(Completer):
    """Completer for debug shell."""

    def __init__(self, libs, keywords, helps, cmd_repl: Optional[PromptToolkitCmd] = None):
        self.names = []
        self.displays = {}
        self.display_metas = {}
        self.helps = helps
        self.libs = libs
        self.keywords = list(keywords)
        self.keywords_catalog = {}
        for keyword in self.keywords:
            self.keywords_catalog[normalize_kw(keyword.name)] = keyword
            self.keywords_catalog[
                f"{normalize_kw(keyword.parent.name)}.{normalize_kw(keyword.name)}"
            ] = keyword
        self.current_statement = None
        for name, display, display_meta in self.get_commands():
            self.names.append(name)
            self.displays[name] = display
            self.display_metas[name] = display_meta
        self.cmd_repl = cmd_repl

    def get_commands(self):
        commands = [(cmd_name, cmd_name, f"DEBUG command: {doc}") for cmd_name, doc in self.helps]

        for lib in self.libs:
            commands.append(
                (
                    lib.name,
                    lib.name,
                    f"Library: {lib.name} {lib.version if hasattr(lib, 'version') else ''}",
                )
            )

        for keyword in self.keywords:
            name = f"{keyword.parent.name}.{keyword.name}"
            commands.append(
                (
                    name,
                    keyword.name,
                    f"({keyword.args})",
                )
            )
            commands.append(
                (
                    keyword.name,
                    keyword.name,
                    f"({keyword.args}) [{keyword.parent.name}]",
                )
            )
        return commands

    def _get_command_completions(self, text):
        suffix_len = len(text) - len(text.rstrip())
        return (
            Completion(
                f"{name}{' ' * suffix_len}",
                -len(text),
                display=self.displays.get(name, ""),
                display_meta=self.display_metas.get(name, ""),
            )
            for name in self.names
            if (
                (("." not in name and "." not in text) or ("." in name and "." in text))
                and normalize_kw(name).startswith(normalize_kw(text))
            )
        )

    def _get_resource_completions(self, text):
        return (
            Completion(
                name,
                -len(text.lstrip()),
                display=name,
                display_meta="",
            )
            for name in [
                "*** Settings ***",
                "*** Variables ***",
                "*** Keywords ***",
            ]
            if (name.lower().strip().startswith(text.strip()))
        )

    def _get_argument_completer(self, text):
        keyword = self.keywords_catalog.get(
            normalize_kw(self.current_statement.statement.keyword), None
        )
        if keyword:
            data_tokens = self.current_statement.statement.data_tokens
            args = keyword.args
            set_named_args, set_pos_args = self.get_set_args(args, data_tokens)
            if set_named_args:
                yield from self.get_named_arg_completion(args, set_named_args, set_pos_args)
            else:
                yield from self.get_pos_arg_completion(args, set_pos_args)

    def get_pos_arg_completion(
        self, args, set_pos_args
    ):  # TODO: here is an issue. if more positional args are set, than existing, named_only will be removed from proposal
        for index, arg in enumerate([*args.positional_or_named, *args.named_only]):
            if index + 1 > len(set_pos_args):
                # suffix = "=" if arg in [*args.positional_or_named, *args.named_only] else ""
                yield Completion(
                    f"{arg}=",
                    0,
                    display=f"{arg}=",
                    display_meta=str(args.defaults.get(arg, "")),
                )

    def get_named_arg_completion(self, args, set_named_args, set_pos_args):
        for index, arg in enumerate([*args.positional_or_named, *args.named_only]):
            if index + 1 > len(set_pos_args) and arg not in set_named_args:
                yield Completion(
                    f"{arg}=",
                    0,
                    display=f"{arg}=",
                    display_meta=str(args.defaults.get(arg, "")),
                )

    def get_set_args(self, args, data_tokens):
        set_named_args = []
        set_pos_args = []
        if len(data_tokens) > 1:
            for arg_token in data_tokens[1:]:
                if arg_token.value:
                    arg_name, sep, arg_value = arg_token.value.partition("=")
                    if sep and arg_name in [*args.positional_or_named, *args.named_only]:
                        set_named_args.append(arg_name)
                    else:
                        set_pos_args.append(arg_token.value)
        return set_named_args, set_pos_args

    def get_completions(self, document, complete_event):
        """Compute suggestions."""
        # RobotFrameworkLocalLexer().parse_doc(document)
        text = document.current_line_before_cursor
        cursor_col = document.cursor_position_col
        cursor_row = document.cursor_position_row
        token_list = list(get_robot_token(document.text))
        statements = list(_tokens_to_statements(token_list, None))
        statement_info = StatementInformation(cursor_col, cursor_row, statements)
        self.current_statement = statement_info
        statement_type = statement_info.statement_type
        previous_token = statement_info.previous_token
        token = statement_info.token
        cursor_pos = statement_info.cursor_pos
        self.cmd_repl.set_toolbar_key(statement_type, token, cursor_pos)
        if text == "":
            yield from []
        elif "FOR".startswith(text):
            yield from [
                Completion(
                    "FOR    ${var}    IN    @{list}\n    Log    ${var}\nEND",
                    -len(text),
                    display="FOR IN",
                    display_meta="For-Loop over all items in a list",
                ),
                Completion(
                    "FOR    ${var}    IN RANGE    5\n    Log    ${var}\nEND",
                    -len(text),
                    display="FOR IN RANGE",
                    display_meta="For-Loop over a range of numbers",
                ),
                Completion(
                    "FOR    ${index}    ${var}    IN ENUMERATE"
                    "    @{list}\n    Log    ${index} - ${var}n\nEND",
                    -len(text),
                    display="FOR IN ENUMERATE",
                    display_meta="For-Loop over all items in a list with index",
                ),
            ]
        elif "IF".startswith(text):
            yield from [
                Completion(
                    "IF    <py-eval>    Log    None",
                    -len(text),
                    display="IF (one line)",
                    display_meta="If-Statement as one line",
                ),
                Completion(
                    "IF    <py-eval>\n    Log    if-branche\nEND",
                    -len(text),
                    display="IF (multi line)",
                    display_meta="If-Statement as multi line",
                ),
            ]
        elif "WHILE".startswith(text):
            yield from [
                Completion(
                    "WHILE    <py-eval>\n    Log    body\nEND",
                    -len(text),
                    display="WHILE loop",
                    display_meta="While-Loop",
                ),
                Completion(
                    "WHILE    <py-eval>     limit=5    on_limit=pass\n    Log    body\nEND",
                    -len(text),
                    display="WHILE loop (with limit)",
                    display_meta="While-Loop with limit and pass when reached",
                ),
            ]
        elif "TRY".startswith(text):
            yield from [
                Completion(
                    "TRY\n    Some Keyword\nEXCEPT\n    Error Handler\nEND",
                    -len(text),
                    display="TRY/EXCEPT Statement",
                    display_meta="Try/Except that catches any error",
                ),
                Completion(
                    "TRY\n    Some Keyword\nEXCEPT    ValueError: *    type=GLOB    AS   ${error}\n    Log    ${error}",
                    -len(text),
                    display="TRY/EXCEPT Statement (specific error)",
                    display_meta="Try/Except that catches a specific error as ${error}",
                ),
            ]
        elif IS_RF_7 and "VAR".startswith(text):
            yield from [
                Completion(
                    "VAR    ${var}    <value>",
                    -len(text),
                    display="VAR (simple)",
                    display_meta="Variable assignment",
                ),
                Completion(
                    "VAR    ${var}    <value>   scope=Suite",
                    -len(text),
                    display="VAR (suite scope)",
                    display_meta="Suite Variable assignment",
                ),
                Completion(
                    "VAR    ${var}    <value>   <value>     separator=${SPACE}",
                    -len(text),
                    display="VAR (multiple values)",
                    display_meta="Variable assignment concatenate",
                ),
            ]
        elif re.fullmatch(r"style {2,}.*", text):
            yield from _get_style_completions(text.lower())
        elif text.startswith("*"):
            yield from self._get_resource_completions(text.lower())
        elif token:
            yield from self._get_keyword_completions(
                cursor_col, cursor_pos, previous_token, statement_type, token
            )

    def _get_keyword_completions(
        self, cursor_col, cursor_pos, previous_token, statement_type, token
    ):
        for var in list(get_variable_token([token])):
            if var.col_offset <= cursor_col <= var.end_col_offset:
                token = var
                cursor_pos = cursor_col - var.col_offset
        SEPARATOR_SIZE = 2
        if token.type in ["ASSIGN", "VARIABLE"] or (
            token.type in ["KEYWORD", "ARGUMENT"] and re.fullmatch(r"[$&@]\{[^}]*}?", token.value)
        ):
            yield from [
                Completion(
                    var,
                    -cursor_pos,
                    display=var,
                    display_meta=repr(val),
                )
                for var, val in BuiltIn().get_variables().items()
                if normalize_kw(var[1:]).startswith(normalize_kw(token.value[1:cursor_pos]))
            ]
        elif token.type == "KEYWORD":
            yield from self._get_command_completions(token.value.lower())
        elif cursor_pos == 1 and previous_token and previous_token.type == "KEYWORD":
            yield from self._get_command_completions(f"{previous_token.value.lower()} ")
        elif (
            token.type in ["SEPARATOR", "EOL"]
            and cursor_pos >= SEPARATOR_SIZE
            and statement_type == "KEYWORD"
        ):
            yield from self._get_argument_completer(token.value)


class KeywordAutoSuggestion(AutoSuggest):
    def __init__(self, completer: CmdCompleter):
        self.completer = completer

    def get_suggestion(self, buffer: Buffer, document: Document) -> Union[Suggestion, None]:
        text = document.text
        completions = [compl.text for compl in self.completer.get_completions(document, None)]
        last_word = KEYWORD_SEP.split(text)[-1]
        matches = [kw for kw in completions if kw.startswith(last_word)]
        matches.extend([kw for kw in completions if kw.lower().startswith(last_word.lower())])
        return Suggestion(matches[0][len(last_word) :] if matches else "")
