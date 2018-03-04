import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import MetadataRetrievalError


class FragmentMetadataRetriever(PluginModule):
    """ Plugin that implements the metadata retrieval stage for a fragment. """

    @abstractmethod
    def retrieve_fragment_metadata(self, doc_var, metadata):
        """
        Retrieves the metadata required to process the fragment.

        :param OrderedDict doc_var: Document variable
        :param dict metadata: Report metadata (overriden by fragment metadata
            when specified)
        :return: Dictionary with metadata
        :rtype: dict
        """
        raise NotImplementedError(
            'Metadata retrieval not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_retriever_exception(cls, context, exception=None,
                                  message=None):
        """
        Returns a metadata retrieval exception with the necessary info
        attached.

        :param dict context: Context for fragment
        :param Exception exception: Exception returned by metadata retrieval
        :param str message: Optional message for exception
        :raises MetadataRetrievalError: always
        """
        exception_info = message if message else str(exception)
        if context.get('fragment_path'):
            location = context['fragment_path']
        else:
            location = '<None>'
        full_msg = '{}: Metadata retrieval error:\n\n{}'.format(
                                                            location,
                                                            exception_info)
        if context.get('logger'):
            logger = logging.getLogger(context['logger'])
            logger.error('[{}] {}'.format(context['doc_suffix'], full_msg))
        err = MetadataRetrievalError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def _get_default_handler(cls, **kwargs):
        """
        In case no explicit plugin is specified, each plugin type can specify
        a default plugin.

        :param dict kwargs: Parameters to decide on a default
        :return: Default plugin
        :rtype: FragmentMetadataRetriever
        """
        extension_dict = {
            '.py': FragmentMetadataRetriever.get('python'),
            '.r': FragmentMetadataRetriever.get('r')
        }
        try:
            extension = kwargs['extension']
        except KeyError:
            raise ValueError('File extension not specified')
        try:
            return extension_dict[extension.lower()]
        except KeyError:
            raise NotImplementedError(
                'No {} specified and no default is available for extension {}'.
                format(cls, extension))

__all__ = ['FragmentMetadataRetriever', ]
