import importlib
import os
from reportcompiler.plugins.context_generators.context_generators \
    import FragmentContextGenerator


class PythonContextGenerator(FragmentContextGenerator):
    """ Context generator for python scripts. """
    name = 'python'

    def generate_context(self, doc_var, data, metadata):
        filename, _ = os.path.splitext(metadata['fragment_path'])
        basename = os.path.basename(filename)
        fragment_module = importlib.import_module(basename)
        context = None
        try:
            context = fragment_module.generate_context(doc_var, data, metadata)
        except Exception as e:
            FragmentContextGenerator.raise_generator_exception(
                metadata, exception=e)
        return context

__all__ = ['PythonContextGenerator', ]
