import pymysql
import pymysql.cursors
import pandas as pd
import pymysql
import pymysql.cursors
from reportcompiler.plugins.data_fetchers.data_fetchers import FragmentDataFetcher


class ExcelFetcher(FragmentDataFetcher):
    name = 'excel'

    def fetch(self, doc_var, fetcher_info, metadata):
        params = [
            {'name': 'file_path', 'default_value': ValueError},
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
                    raise FragmentDataFetcher.raise_data_fetching_exception(metadata['fragment_path'], None, metadata,
                                                                     message='Parameter {} is missing'.format(param['name']))
                else:
                    par = param['default_value']
            arguments[param['name']] = par

        df = pd.read_excel(io=arguments['file_path'],
                           sheet_name=arguments['sheet_name'],
                           usecols=arguments['columns'],
                           na_values=arguments['na_values'])
        return df
