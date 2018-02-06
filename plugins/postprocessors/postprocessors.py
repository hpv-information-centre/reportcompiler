import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import PostProcessorError


class PostProcessor(PluginModule):

    @abstractmethod
    def postprocess(self, doc_var, doc, postprocessor_info, context):
        raise NotImplementedError('Postprocessing not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_postprocessor_exception(cls, exception, context, message=None):
        exception_info = message if message else str(exception)
        full_msg = 'Postprocessing error:\n\n{}'.format(exception_info)
        logger = logging.getLogger(context['meta']['logger'])
        logger.error('[{}] {}'.format(context['meta']['doc_suffix'], full_msg))
        err = PostProcessorError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None
