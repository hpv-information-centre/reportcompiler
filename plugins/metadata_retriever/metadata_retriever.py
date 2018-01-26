from abc import abstractmethod
import logging
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import MetadataRetrievalError


class FragmentMetadataRetriever(PluginModule):

    @abstractmethod
    def retrieve_fragment_metadata(self, doc_var, metadata):
        raise NotImplementedError('Metadata retrieval not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_retriever_exception(cls, filename, exception, context, message=None):
        exception_info = message if message else str(exception)
        full_msg = '{}: Metadata retrieval error:\n\n{}'.format(filename, exception_info)
        logger = logging.getLogger(context['logger'])
        logger.error('[{}] {}'.format(context['doc_suffix'], full_msg))
        err = MetadataRetrievalError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def _get_default_handler(cls, extension):
        extension_dict = {
            '.py': FragmentMetadataRetriever.get('python'),
            '.r': FragmentMetadataRetriever.get('r')
        }
        try:
            return extension_dict[extension]
        except KeyError:
            raise NotImplementedError('No {} specified and no default is available for extension {}'.format(cls, extension))
