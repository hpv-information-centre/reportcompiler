import pandas as pd
from reportcompiler.plugins.data_fetchers.data_fetchers \
    import FragmentDataFetcher


class StubFetcher(FragmentDataFetcher):
    """ Stub data fetcher. """
    name = 'stub'

    def fetch(self, doc_var, fetcher_info, metadata):
        try:
            arg = doc_var['text']
        except KeyError:
            arg = 'No arguments'
        return pd.DataFrame([['It works!', arg]],
                            columns=['first_col', 'second_col'])

__all__ = ['StubFetcher', ]
