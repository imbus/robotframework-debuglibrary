from copy import deepcopy

from robot.libdocpkg.model import LibraryDoc
from robot.libdocpkg.robotbuilder import (
    KeywordDocBuilder,
    LibraryDocBuilder,
    ResourceDocBuilder,
)
from robot.libraries import STDLIBS
from robot.libraries.BuiltIn import BuiltIn


def get_builtin_libs():
    """Get robotframework builtin library names."""
    return list(STDLIBS)


def get_libs():
    """Get imported robotframework library names."""
    libs = get_libraries()
    resources = get_resources()
    libs.extend(resources)
    return sorted(libs, key=lambda _: _.name)


def get_libraries():
    return [
        lib for lib in BuiltIn()._namespace._kw_store.libraries.values() if lib.name != "Reserved"
    ]


def get_resources():
    return BuiltIn()._namespace._kw_store.resources._items


def match_libs(name=""):
    """Find libraries by prefix of library name, default all"""
    return [lib for lib in get_libs() if lib.name.lower().startswith(name.lower())]


class ImportedResourceDocBuilder(ResourceDocBuilder):
    def build(self, resource):
        libdoc = LibraryDoc(
            name=resource.name,
            doc=self._get_doc(resource, resource.name),
            type="RESOURCE",
            scope="GLOBAL",
        )
        libdoc.keywords = KeywordDocBuilder().build_keywords(deepcopy(resource))
        return libdoc


class ImportedLibraryDocBuilder(LibraryDocBuilder):
    def build(self, lib):
        libdoc = LibraryDoc(
            doc=self._get_doc(lib),
            version=lib.version,
            scope=str(lib.scope),
            doc_format=lib.doc_format,
            source=lib.source,
            lineno=lib.lineno,
            name=lib.name,
        )
        libdoc.inits = self._get_initializers(lib)
        libdoc.keywords = KeywordDocBuilder().build_keywords(lib)
        libdoc.type_docs = self._get_type_docs(libdoc.inits + libdoc.keywords, lib.converters)
        return libdoc
