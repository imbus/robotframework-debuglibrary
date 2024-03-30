import tempfile
from pathlib import Path
from typing import Iterator, List, Tuple

from robot.libdocpkg.model import KeywordDoc, LibraryDoc
from robot.libraries.BuiltIn import BuiltIn
from robot.parsing import get_model
from robot.running import TestSuite

try:
    from robot.running import UserLibrary as ResourceFile
except ImportError:
    from robot.running import ResourceFile
from robot.variables.search import is_variable

from .globals import KEYWORD_SEP
from .robotlib import ImportedLibraryDocBuilder, ImportedResourceDocBuilder, get_libs

_lib_keywords_cache = {}
_resource_keywords_cache = {}
temp_resources = []


def parse_keyword(command) -> Tuple[List[str], str, List[str]]:
    """Split a robotframework keyword string."""
    # TODO use robotframework functions
    variables = []
    keyword = ""
    args = []
    parts = KEYWORD_SEP.split(command)
    for part in parts:
        if not keyword and is_variable(part.rstrip("=").strip()):
            variables.append(part.rstrip("=").strip())
        elif not keyword:
            keyword = part
        else:
            args.append(part)
    return variables, keyword, args


def get_lib_keywords(library) -> List[KeywordDoc]:
    """Get keywords of imported library."""
    if library.name not in _lib_keywords_cache:
        if isinstance(library, ResourceFile):
            _lib_keywords_cache[library.name]: LibraryDoc = ImportedResourceDocBuilder().build(
                library
            )
        else:
            _lib_keywords_cache[library.name]: LibraryDoc = ImportedLibraryDocBuilder().build(
                library
            )
    return _lib_keywords_cache[library.name].keywords


def get_keywords() -> Iterator[KeywordDoc]:
    """Get all keywords of libraries."""
    for lib in get_libs():
        yield from get_lib_keywords(lib)


def find_keyword(keyword_name) -> List[KeywordDoc]:
    keyword_name = keyword_name.lower()
    return [
        keyword
        for lib in get_libs()
        for keyword in get_lib_keywords(lib)
        if normalize_kw(keyword.name) == normalize_kw(keyword_name)
    ]


def normalize_kw(keyword_name):
    return keyword_name.lower().replace("_", "").replace(" ", "")


def get_test_body_from_string(command):
    if "\n" in command:
        command = "\n  ".join(command.split("\n"))
    suite_str = f"""
*** Test Cases ***
Fake Test
  {command}
"""
    model = get_model(suite_str)
    suite: TestSuite = TestSuite.from_model(model)
    return suite.tests[0]


def _import_resource_from_string(command):
    res_file = tempfile.NamedTemporaryFile(
        mode="w",
        prefix="RobotDebug_keywords_",
        suffix=".resource",
        encoding="utf-8",
        delete=False,
    )
    resource_path = Path(res_file.name)
    try:
        res_file.write(command)
        res_file.close()
        temp_resources.insert(0, str(resource_path.stem))
        BuiltIn().import_resource(resource_path.resolve().as_posix())
        BuiltIn().set_library_search_order(*temp_resources)
    finally:
        resource_path.unlink(missing_ok=True)


def _get_assignments(body_elem):
    if hasattr(body_elem, "assign"):
        yield from body_elem.assign
    elif hasattr(body_elem, "body"):
        for child in body_elem.body:
            yield from _get_assignments(child)
    elif body_elem.type == "VAR":
        yield body_elem.name


def run_debug_if(condition, *args):
    """Runs DEBUG if condition is true."""

    return BuiltIn().run_keyword_if(condition, "RobotDebug.DEBUG", *args)
