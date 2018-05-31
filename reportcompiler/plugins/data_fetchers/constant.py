""" constant.py

This module includes the data fetcher using a constant list (given as a
parameter).

"""

import pandas as pd
from reportcompiler.plugins.data_fetchers.base \
    import DataFetcher

__all__ = ['ConstantFetcher', ]


class ConstantFetcher(DataFetcher):
    """ Constant data fetcher. """

    def fetch(self, doc_param, fetcher_info, metadata):
        try:
            values = fetcher_info['values']
            if not isinstance(values, list):
                raise DataFetcher.raise_data_fetching_exception(
                    metadata,
                    message="Constant fetcher values not a list.")

            col_name = fetcher_info.get('name')
            return pd.DataFrame(data=values,
                                columns=['value'
                                         if col_name is None
                                         else col_name])
        except KeyError:
            # Since this fetcher is the default one, not finding the
            # 'values' key might mean that the user forgot the 'type'
            # key for a different fetcher.
            raise DataFetcher.raise_data_fetching_exception(
                metadata,
                message="The 'type' or 'values' keys are not set.")
