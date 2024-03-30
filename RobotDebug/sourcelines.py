from pathlib import Path
from typing import List, Tuple

from pygments.token import Token

from RobotDebug.lexer import (
    RobotFrameworkLocalLexer,
    get_robot_token_from_file,
)
from RobotDebug.styles import print_output, print_pygments_styles

LINE_NO_TOKEN = Token.Operator.LineNumber


def print_source_lines(style, source_file, lineno, before_and_after=5):
    if not source_file or not lineno:
        return

    Path(
        source_file
    ).open().readlines()  # noqa: SIM115  TODO: not sure why i did this. Maybe to check if file is actually readable...
    prefixed_token = get_pygments_token_from_file(lineno, source_file)
    printable_token = filter_token_by_lineno(
        prefixed_token, lineno - before_and_after, lineno + before_and_after + 1
    )
    print_pygments_styles(printable_token, style)


def print_test_case_lines(style, source_file, current_lineno):
    if not source_file or not current_lineno:
        return

    Path(
        source_file
    ).open().readlines()  # noqa: SIM115  TODO: not sure why i did this. Maybe to check if file is actually readable...
    prefixed_token = get_pygments_token_from_file(current_lineno, source_file)
    printable_token = filter_token_by_scope(prefixed_token, current_lineno)
    print_pygments_styles(printable_token, style)


def filter_token_by_lineno(token, start_lineno, end_lineno):
    current_lineno = 0
    for tok, val in token:
        if tok == LINE_NO_TOKEN:
            current_lineno += 1
        if start_lineno <= current_lineno < end_lineno:
            yield tok, val


def filter_token_by_scope(token, current_lineno):
    rf_to_py = RobotFrameworkLocalLexer.ROBOT_TO_PYGMENTS
    scope_start_lineno = 0
    scope_end_lineno = 1000000
    line_found = False
    lineno = 0
    all_token = list(token)
    for tok, _val in all_token:
        if tok == LINE_NO_TOKEN:
            lineno += 1
        if not line_found and tok in [rf_to_py["HEADER"], rf_to_py["DEFINITION"]]:
            scope_start_lineno = lineno
        if lineno == current_lineno:
            line_found = True
        if line_found and tok in [rf_to_py["HEADER"], rf_to_py["DEFINITION"]]:
            scope_end_lineno = lineno
            break
    filtered_token = list(filter_token_by_lineno(all_token, scope_start_lineno, scope_end_lineno))

    tokens_to_remove = 0
    for tok, val in reversed(filtered_token):
        if tok == LINE_NO_TOKEN or val == "\n" or not val.strip():
            tokens_to_remove += 1
        else:
            break
    if tokens_to_remove:
        return filtered_token[:-tokens_to_remove]
    return filtered_token


def get_pygments_token_from_file(current_lineno, source_file):
    token = get_robot_token_from_file(Path(source_file))
    pygments_token = list(RobotFrameworkLocalLexer().get_pygments_token(token))
    return prefix_line_numbers_and_position(pygments_token, current_lineno)


def prefix_line_numbers_and_position(token: List[Tuple], lineno):
    """prefix each line with a pygment token of line number and add an arrow in the line of lineno"""
    line_number = 1
    yield LINE_NO_TOKEN, f"{line_number:>3}   "
    for tok, val in token:
        yield tok, val
        if val == "\n":
            line_number += 1
            if line_number == lineno:
                yield LINE_NO_TOKEN, f"{line_number:>3} ->"
            else:
                yield LINE_NO_TOKEN, f"{line_number:>3}   "


def _find_last_lineno(lines, begin_lineno):
    line_index = begin_lineno - 1
    while line_index < len(lines):
        line = lines[line_index]
        if not _inside_test_case_block(line):
            break
        line_index += 1
    return line_index


def _find_first_lineno(lines, begin_lineno):
    line_index = begin_lineno - 1
    while line_index >= 0:
        line_index -= 1
        line = lines[line_index]
        if not _inside_test_case_block(line):
            break
    return line_index


def _inside_test_case_block(line):
    if line.startswith(" "):
        return True
    if line.startswith("\t"):
        return True
    if line.startswith("#"):
        return True
    return False


def _print_lines(lines, start_index, end_index, current_lineno):
    display_lines = lines[start_index:end_index]
    for lineno, line in enumerate(display_lines, start_index + 1):
        current_line_sign = ""
        if lineno == current_lineno:
            current_line_sign = "->"
        print_output(f"{lineno:>3} {current_line_sign:2}\t", f"{line.rstrip()}")
