""" python.py

This module includes the source parser using python.

"""

import importlib
import os
from reportcompiler.plugins.source_parsers.base \
    import SourceParser

__all__ = ['PythonParser', ]


class PythonParser(SourceParser):
    """ Context generator for python scripts. """

    def generate_context(self, doc_var, data, metadata):
        filename, _ = os.path.splitext(metadata['fragment_path'])
        basename = os.path.basename(filename)
        fragment_module = importlib.import_module(basename)
        context = None
        try:
            context = fragment_module.generate_context(doc_var, data, metadata)
        except Exception as e:
            SourceParser.raise_generator_exception(
                metadata, exception=e)
        return context

    def retrieve_fragment_metadata(self, doc_var, metadata):
        module_name = metadata['fragment_name']

        fragment_module = None
        try:
            fragment_module = importlib.import_module(module_name)
        except Exception as e:
            SourceParser.raise_retriever_exception(
                metadata, exception=e)

        module_vars = {var: fragment_module.__dict__[var]
                       for var in dir(fragment_module)
                       if (not callable(fragment_module.__dict__[var]) and
                           not var.startswith('__'))}
        return module_vars