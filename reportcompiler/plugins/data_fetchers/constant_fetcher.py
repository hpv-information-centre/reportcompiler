import pandas as pd
from reportcompiler.plugins.data_fetchers.data_fetchers \
    import FragmentDataFetcher


class ConstantFetcher(FragmentDataFetcher):
    """ Constant data fetcher. """
    name = 'constant'

    def fetch(self, doc_var, fetcher_info, metadata):
        try:
            values = fetcher_info['values']
            if not isinstance(values, list):
                raise FragmentDataFetcher.raise_data_fetching_exception(
                    metadata['fragment_path'],
                    None,
                    metadata,
                    message="Constant fetcher values not a list.")

            return pd.DataFrame(data=values,
                                columns=['value'])
        except KeyError:
            # Since this fetcher is the default one, not finding the
            # 'values' key might mean that the user forgot the 'type'
            # key for a different fetcher.
            raise FragmentDataFetcher.raise_data_fetching_exception(
                metadata['fragment_path'],
                None,
                metadata,
                message="The 'type' or 'values' keys are not set.")

__all__ = ['ConstantFetcher', ]
