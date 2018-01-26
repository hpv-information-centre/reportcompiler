from abc import abstractmethod
import logging
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import DataFetchingError


class FragmentDataFetcher(PluginModule):

    @abstractmethod
    def fetch(self, doc_var, fetcher_info, metadata):
        raise NotImplementedError('Data fetching not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_data_fetching_exception(cls, filename, exception, context, message=None):
        exception_info = message if message else str(exception)
        full_msg = '{}: Data fetching error:\n\n{}'.format(filename, exception_info)
        logger = logging.getLogger(context['logger'])
        logger.error('[{}] {}'.format(context['doc_suffix'], full_msg))
        err = DataFetchingError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None
