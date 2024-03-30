import re
from pathlib import Path
from typing import ClassVar, Dict, List

from pygments.lexer import Lexer
from pygments.token import Token, _TokenType
from robot.parsing import get_tokens


def get_robot_token_from_file(file: Path):
    return list(get_tokens(file))


HEADER_MATCHER = re.compile(
    r"\s*\*+ ?(keywords?|settings?|variables?|comments?) ?\**", re.IGNORECASE
)


def get_robot_token(text):
    if HEADER_MATCHER.match(text):
        yield from get_tokens(text)
    else:
        marker_len = 20
        new_line_start = " " * marker_len
        if "\n" in text:
            text = f"\n{new_line_start}".join(text.split("\n"))
        suite_str = f"*** Test Cases ***\nFake Test\n{new_line_start}{text}"
        for token in list(get_tokens(suite_str))[6:]:
            if (
                token.type in ["SEPARATOR", "EOL"]
                and token.col_offset == 0
                and token.end_col_offset >= marker_len
            ):
                if token.end_col_offset == marker_len:
                    continue
                token.value = token.value[marker_len:]
                token.col_offset = 0
                token.lineno = token.lineno - 2
            else:
                token.col_offset = token.col_offset - marker_len
                token.lineno = token.lineno - 2
            yield token


def get_variable_token(token_list):
    for token in token_list:
        if len(token.value) == 0:
            continue
        try:
            var_tokens = list(token.tokenize_variables())
        except Exception:
            var_tokens = [token]
        yield from var_tokens


class RobotFrameworkLocalLexer(Lexer):
    name = "RobotFramework"
    url = "http://robotframework.org"
    aliases: ClassVar[List[str]] = ["robotframework"]
    filenames: ClassVar[List[str]] = ["*.robot", "*.resource"]
    mimetypes: ClassVar[List[str]] = ["text/x-robotframework"]

    # PYGMENTS_STANDARD_TYPES = {
    #     Token: '',
    #
    #     Text: '',
    #     Whitespace: 'w',
    #     Escape: 'esc',
    #     Error: 'err',
    #     Other: 'x',
    #
    #     Keyword: 'k',
    #     Keyword.Constant: 'kc',
    #     Keyword.Declaration: 'kd',
    #     Keyword.Namespace: 'kn',
    #     Keyword.Pseudo: 'kp',
    #     Keyword.Reserved: 'kr',
    #     Keyword.Type: 'kt',
    #
    #     Name: 'n',
    #     Name.Attribute: 'na',
    #     Name.Builtin: 'nb',
    #     Name.Builtin.Pseudo: 'bp',
    #     Name.Class: 'nc',
    #     Name.Constant: 'no',
    #     Name.Decorator: 'nd',
    #     Name.Entity: 'ni',
    #     Name.Exception: 'ne',
    #     Name.Function: 'nf',
    #     Name.Function.Magic: 'fm',
    #     Name.Property: 'py',
    #     Name.Label: 'nl',
    #     Name.Namespace: 'nn',
    #     Name.Other: 'nx',
    #     Name.Tag: 'nt',
    #     Name.Variable: 'nv',
    #     Name.Variable.Class: 'vc',
    #     Name.Variable.Global: 'vg',
    #     Name.Variable.Instance: 'vi',
    #     Name.Variable.Magic: 'vm',
    #
    #     Literal: 'l',
    #     Literal.Date: 'ld',
    #
    #     String: 's',
    #     String.Affix: 'sa',
    #     String.Backtick: 'sb',
    #     String.Char: 'sc',
    #     String.Delimiter: 'dl',
    #     String.Doc: 'sd',
    #     String.Double: 's2',
    #     String.Escape: 'se',
    #     String.Heredoc: 'sh',
    #     String.Interpol: 'si',
    #     String.Other: 'sx',
    #     String.Regex: 'sr',
    #     String.Single: 's1',
    #     String.Symbol: 'ss',
    #
    #     Number: 'm',
    #     Number.Bin: 'mb',
    #     Number.Float: 'mf',
    #     Number.Hex: 'mh',
    #     Number.Integer: 'mi',
    #     Number.Integer.Long: 'il',
    #     Number.Oct: 'mo',
    #
    #     Operator: 'o',
    #     Operator.Word: 'ow',
    #
    #     Punctuation: 'p',
    #     Punctuation.Marker: 'pm',
    #
    #     Comment: 'c',
    #     Comment.Hashbang: 'ch',
    #     Comment.Multiline: 'cm',
    #     Comment.Preproc: 'cp',
    #     Comment.PreprocFile: 'cpf',
    #     Comment.Single: 'c1',
    #     Comment.Special: 'cs',
    #
    #     Generic: 'g',
    #     Generic.Deleted: 'gd',
    #     Generic.Emph: 'ge',
    #     Generic.Error: 'gr',
    #     Generic.Heading: 'gh',
    #     Generic.Inserted: 'gi',
    #     Generic.Output: 'go',
    #     Generic.Prompt: 'gp',
    #     Generic.Strong: 'gs',
    #     Generic.Subheading: 'gu',
    #     Generic.Traceback: 'gt',
    # }

    ROBOT_TO_PYGMENTS: ClassVar[Dict[str, _TokenType]] = {
        "HEADER": Token.Keyword.Namespace,
        "DEFINITION": Token.Name.Class,
        "SETTING HEADER": Token.Keyword.Namespace,
        "VARIABLE HEADER": Token.Keyword.Namespace,
        "TESTCASE HEADER": Token.Keyword.Namespace,
        "TASK HEADER": Token.Keyword.Namespace,
        "KEYWORD HEADER": Token.Keyword.Namespace,
        "COMMENT HEADER": Token.Keyword.Namespace,
        "TESTCASE NAME": Token.Name.Class,
        "KEYWORD NAME": Token.Name.Class,
        "DOCUMENTATION": Token.Name.Label,
        "SUITE SETUP": Token.Name.Label,
        "SUITE TEARDOWN": Token.Name.Label,
        "METADATA": Token.Name.Label,
        "TEST SETUP": Token.Name.Label,
        "TEST TEARDOWN": Token.Name.Label,
        "TEST TEMPLATE": Token.Name.Label,
        "TEST TIMEOUT": Token.Name.Label,
        "FORCE TAGS": Token.Name.Label,
        "DEFAULT TAGS": Token.Name.Label,
        "KEYWORD TAGS": Token.Name.Label,
        "LIBRARY": Token.Name.Label,
        "RESOURCE": Token.Name.Label,
        "VARIABLES": Token.Name.Label,
        "SETUP": Token.Name.Property,
        "TEARDOWN": Token.Name.Property,
        "TEMPLATE": Token.Name.Property,
        "TIMEOUT": Token.Name.Property,
        "TAGS": Token.Name.Property,
        "ARGUMENTS": Token.Name.Property,
        "RETURN_SETTING": Token.Name.Property,
        "NAME": Token.Name,
        "VARIABLE": Token.Name.Variable.Instance,
        "ARGUMENT": Token.String,
        "ASSIGN": Token.Name.Variable,
        "KEYWORD": Token.Name.Function,
        "WITH NAME": Token.Keyword,
        "FOR": Token.Keyword,
        "FOR SEPARATOR": Token.Keyword,
        "END": Token.Keyword,
        "IF": Token.Keyword,
        "INLINE IF": Token.Keyword,
        "ELSE IF": Token.Keyword,
        "ELSE": Token.Keyword,
        "TRY": Token.Keyword,
        "EXCEPT": Token.Keyword,
        "FINALLY": Token.Keyword,
        "AS": Token.Keyword,
        "WHILE": Token.Keyword,
        "RETURN STATEMENT": Token.Keyword,
        "CONTINUE": Token.Keyword,
        "BREAK": Token.Keyword,
        "OPTION": Token.Keyword,
        "VAR": Token.Keyword,
        "SEPARATOR": Token.Punctuation,
        "COMMENT": Token.Comment,
        "CONTINUATION": Token.Operator,
        "CONFIG": Token.Punctuation,
        "EOL": Token.Punctuation,
        "EOS": Token.Punctuation,
        "ERROR": Token.Error,
        "FATAL ERROR": Token.Error,
    }

    def __init__(self, **options):
        options["tabsize"] = 2
        options["encoding"] = "UTF-8"
        Lexer.__init__(self, **options)

    # def parse_doc(self, document):
    #     text = document.text
    #     cursor_col = document.cursor_position_col
    #     cursor_row = document.cursor_position_row
    #     doc_tokens = list(Tokenizer().tokenize(text))
    #     # statements = _tokens_to_statements(tok)
    #     statement_at_cursor, token_at_cursor = self.tokenize_statement(cursor_col, cursor_row, doc_tokens)
    #     pygments_tokens = list(RobotFrameworkLexer().get_tokens_unprocessed(text))
    #     return doc_tokens, statement_at_cursor, token_at_cursor
    #
    # def tokenize_statement(self, cursor_col, cursor_row, doc_tokens):
    #     statement_at_cursor = None
    #     token_at_cursor = None
    #     for statement in doc_tokens:
    #         content_token = [token for token in statement if token.type not in ["SEPARATOR", "EOL", "CONTINUATION"]]
    #         kwl = KeywordCallLexer(ResourceFileContext())
    #         kwl.input(content_token)
    #         kwl._lex_as_keyword_call()
    #         if not token_at_cursor:
    #             for token in statement:
    #                 if token.lineno - 1 == cursor_row:
    #                     if token.col_offset <= cursor_col < token.end_col_offset:
    #                         token_at_cursor = token
    #                         statement_at_cursor = statement
    #                         break
    #     return statement_at_cursor, token_at_cursor

    def get_tokens_unprocessed(self, text):
        token_list = get_robot_token(text)
        index = 0
        for v_token in get_variable_token(token_list):
            yield index, self.to_pygments_token_type(v_token), v_token.value
            index += len(v_token.value)

    def get_pygments_token(self, token):
        for v_token in get_variable_token(token):
            yield self.to_pygments_token_type(v_token), v_token.value

    def to_pygments_token_type(self, token):
        if token.type == "VARIABLE":
            if re.match(r"[$&@%]\{(EMPTY|TRUE|FALSE|NONE)}", token.value, re.IGNORECASE):
                return Token.Name.Constant
            if re.match(r"\$\{\d+}", token.value):
                return Token.Name.Constant
        return self.ROBOT_TO_PYGMENTS.get(token.type, Token.Generic.Error)
