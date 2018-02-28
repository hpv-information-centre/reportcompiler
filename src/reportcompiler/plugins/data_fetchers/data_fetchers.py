import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import DataFetchingError


class FragmentDataFetcher(PluginModule):
    """ Plugin that implements the data fetching stage for a fragment. """

    @abstractmethod
    def fetch(self, doc_var, fetcher_info, metadata):
        """
        Fetches the necessary data for the current fragment.

        :param OrderedDict doc_var: Document variable
        :param dict fetcher_info: Information about the current fetcher
            (multiple can be used for fragment)
        :param dict metadata: Report metadata (overriden by fragment metadata
            when specified)
        :return: Dataframe (or list of dataframes)
        :rtype: pandas.DataFrame
        """
        raise NotImplementedError(
            'Data fetching not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_data_fetching_exception(cls, filename, exception, context,
                                      message=None):
        """
        Returns a data fetching exception with the necessary info attached.

        :param str filename: Fragment filename
        :param Exception exception: Exception returned by data fetching
        :param dict context: Context for fragment
        :param str message: Optional message for exception
        """
        exception_info = message if message else str(exception)
        full_msg = '{}: Data fetching error:\n\n{}'.format(filename,
                                                           exception_info)
        logger = logging.getLogger(context['logger'])
        logger.error('[{}] {}'.format(context['doc_suffix'], full_msg))
        err = DataFetchingError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def _get_default_handler(cls, **kwargs):
        return FragmentDataFetcher.get('constant')

__all__ = ['FragmentDataFetcher', ]
