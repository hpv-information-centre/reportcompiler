""" excel.py

This module includes the data fetcher using Excel worksheets.

"""


import os
import pandas as pd
from reportcompiler.plugins.data_fetchers.base \
    import DataFetcher


class ExcelFetcher(DataFetcher):
    """ Data fetcher for excel files. """
    name = 'excel'

    def fetch(self, doc_var, fetcher_info, metadata):
        params = [
            {'name': 'file', 'default_value': ValueError},
            {'name': 'sheet_name', 'default_value': 0},
            {'name': 'columns', 'default_value': None},
            {'name': 'na_values', 'default_value': None},
        ]

        arguments = {}
        for param in params:
            try:
                par = fetcher_info[param['name']]
            except KeyError:
                if isinstance(param['default_value'], ValueError):
                    raise DataFetcher.raise_data_fetching_exception(
                            metadata,
                            message='Parameter {} is missing'.format(
                                         param['name']))
                else:
                    par = param['default_value']
            arguments[param['name']] = par

        filename = os.path.basename(arguments['file'])
        file_path = os.path.join(metadata['data_path'],
                                 filename)

        df = pd.read_excel(io=file_path,
                           sheet_name=arguments['sheet_name'],
                           usecols=arguments['columns'],
                           na_values=arguments['na_values'])
        return df

__all__ = ['ExcelFetcher', ]
