import pandas as pd
from reportcompiler.plugins.data_fetchers.base \
    import DataFetcher


class ConstantFetcher(DataFetcher):
    """ Constant data fetcher. """
    name = 'constant'

    def fetch(self, doc_var, fetcher_info, metadata):
        try:
            values = fetcher_info['values']
            if not isinstance(values, list):
                raise DataFetcher.raise_data_fetching_exception(
                    metadata,
                    message="Constant fetcher values not a list.")

            return pd.DataFrame(data=values,
                                columns=['value'])
        except KeyError:
            # Since this fetcher is the default one, not finding the
            # 'values' key might mean that the user forgot the 'type'
            # key for a different fetcher.
            raise DataFetcher.raise_data_fetching_exception(
                metadata,
                message="The 'type' or 'values' keys are not set.")

__all__ = ['ConstantFetcher', ]