import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import PostProcessorError


class PostProcessor(PluginModule):
    """ Plugin that implements the postprocessing stage for the document (see
    architecture). """

    @abstractmethod
    def postprocess(self, doc_var, doc, postprocessor_info, context):
        """
        Applies the postprocessing after the document has been rendered.

        :param OrderedDict doc_var: Document variable
        :param dict postprocessor_info: Information about the current
            postprocessor (multiple can be used for fragment)
        :param dict context: Context dictionary with keys 'data' (context
            generated from fragments) and 'meta' (report metadata)
        """
        raise NotImplementedError(
            'Postprocessing not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_postprocessor_exception(cls, exception, context, message=None):
        """
        Returns a postprocessing exception with the necessary info attached.

        :param str filename: Fragment filename
        :param Exception exception: Exception returned by metadata retrieval
        :param dict context: Context for fragment
        :param str message: Optional message for exception
        """
        exception_info = message if message else str(exception)
        full_msg = 'Postprocessing error:\n\n{}'.format(exception_info)
        logger = logging.getLogger(context['meta']['logger'])
        logger.error('[{}] {}'.format(context['meta']['doc_suffix'], full_msg))
        err = PostProcessorError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

__all__ = ['PostProcessor', ]