from inspect import signature
from robot.libdocpkg.model import LibraryDoc
from robot.libdocpkg.robotbuilder import KeywordDocBuilder, LibraryDocBuilder
from robot.libraries import STDLIBS
from robot.running.namespace import IMPORTER


def get_builtin_libs():
    """Get robotframework builtin library names."""
    return list(STDLIBS)


def get_libs():
    """Get imported robotframework library names."""
    return sorted(IMPORTER._library_cache._items, key=lambda _: _.name)


def get_libs_dict():
    """Get imported robotframework libraries as a name -> lib dict"""
    return {lib.name: lib for lib in IMPORTER._library_cache._items}


def match_libs(name=''):
    """Find libraries by prefix of library name, default all"""
    libs = [_.name for _ in get_libs()]
    matched = [_ for _ in libs if _.lower().startswith(name.lower())]
    return matched


class ImportedLibraryDocBuilder(LibraryDocBuilder):
    def __init__(self):
        # Base class requires doc_format since RF 7.5; don't remove.
        self.doc_format = None

    def build(self, lib):
        libdoc = LibraryDoc(
            name=lib.name,
            doc=self._get_doc(lib),
            doc_format=self.doc_format
        )
        libdoc.inits = self._get_initializers(lib)
        libdoc.keywords = KeywordDocBuilder().build_keywords(lib)
        return libdoc
