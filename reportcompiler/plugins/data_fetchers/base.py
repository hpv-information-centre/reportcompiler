""" base.py

This module includes the base plugin interface for data fetchers.

"""

import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import DataFetchingError

__all__ = ['DataFetcher', ]


class DataFetcher(PluginModule):
    """ Plugin that implements the data fetching stage for a fragment. """

    entry_point_group = 'data_fetchers'

    @abstractmethod
    def fetch(self, doc_var, fetcher_info, metadata):
        """
        Fetches the necessary data for the current fragment.

        :param OrderedDict doc_var: Document variable
        :param dict fetcher_info: Information about the current fetcher
            (multiple can be used for fragment)
        :param dict metadata: Report metadata (overriden by fragment metadata
            when specified)
        :returns: Dataframe (or list of dataframes)
        :rtype: pandas.DataFrame
        """
        raise NotImplementedError(
            'Data fetching not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_data_fetching_exception(cls, context, exception=None,
                                      message=None):
        """
        Returns a data fetching exception with the necessary info attached.

        :param dict context: Context for fragment
        :param Exception exception: Exception returned by data fetching
        :param str message: Optional message for exception
        :raises DataFetchingError: always
        """
        exception_info = message if message else str(exception)
        if context.get('fragment_path'):
            location = context['fragment_path']
        else:
            location = 'config.json'
        full_msg = '{}: Data fetching error:\n\n{}'.format(location,
                                                           exception_info)
        if context.get('logger_name'):
            logger = logging.getLogger(context['logger_name'])
            logger.error('[{}] {}'.format(context['doc_suffix'], full_msg))
        err = DataFetchingError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def _get_default_handler(cls, **kwargs):
        return DataFetcher.get('constant')
