import importlib
import importlib.util
from reportcompiler.plugins.metadata_retriever.metadata_retriever \
    import FragmentMetadataRetriever


class PythonMetadataRetriever(FragmentMetadataRetriever):
    """ Metadata retriever for python scripts. """
    name = 'python'

    def retrieve_fragment_metadata(self, doc_var, metadata):
        module_name = metadata['fragment_name']

        fragment_module = None
        try:
            fragment_module = importlib.import_module(module_name)
        except Exception as e:
            FragmentMetadataRetriever.raise_retriever_exception(
                metadata, exception=e)

        module_vars = {var: fragment_module.__dict__[var]
                       for var in dir(fragment_module)
                       if (not callable(fragment_module.__dict__[var]) and
                           not var.startswith('__'))}
        return module_vars

__all__ = ['PythonMetadataRetriever', ]
