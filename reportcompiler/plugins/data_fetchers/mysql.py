import pymysql.cursors
import pymysql
import pymysql.cursors
import pandas as pd
import os
import json
import logging
from threading import Lock
from pymysql.err import OperationalError
from reportcompiler.plugins.data_fetchers.base \
    import DataFetcher
from reportcompiler.plugins.data_fetchers.utils.sql \
    import SQLQueryBuilder


class MySQLFetcher(DataFetcher):
    """ Data fetcher for MySQL databases. """
    name = 'mysql'
    mutex = Lock()

    @staticmethod
    def create_connection(credentials):
        connection = pymysql.connect(host=credentials['host'],
                                     user=credentials['user'],
                                     password=credentials['password'],
                                     db=credentials['db'],
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        return connection

    def fetch(self, doc_var, fetcher_info, metadata):
        # TODO: Look for ways to avoid mutex
        with MySQLFetcher.mutex:
            data = self._fetch(doc_var, fetcher_info, metadata)
        return data

    def _fetch(self, doc_var, fetcher_info, metadata):
        credentials = MySQLFetcher._create_context_credentials(fetcher_info,
                                                               metadata)
        try:
            connection = MySQLFetcher.create_connection(credentials)
        except OperationalError as e:
            raise DataFetcher.raise_data_fetching_exception(
                    metadata,
                    exception=e)

        try:
            sql_string = SQLQueryBuilder(doc_var,
                                         fetcher_info,
                                         metadata).build()
        except KeyError:
            raise DataFetcher.raise_data_fetching_exception(
                metadata,
                message='Table/column definition not defined for fragment')

        df = pd.read_sql(sql_string, con=connection)
        return df

    @staticmethod
    def _create_context_credentials(fetcher_info, metadata):
        credentials = None

        try:
            with open(os.path.join(metadata['report_path'],
                                   'credentials',
                                   fetcher_info['credentials_file'] + '.json'),
                      'r') as cred_file:
                credentials = json.load(cred_file)
        except KeyError:
            pass

        if credentials is None:
            credentials = {}
            try:
                credentials['host'] = fetcher_info['host']
                credentials['user'] = fetcher_info['user']
                credentials['password'] = fetcher_info['password']
                credentials['db'] = fetcher_info['db']
            except KeyError:
                raise DataFetcher.raise_data_fetching_exception(
                    metadata,
                    message='MySQL credentials not specified in context')
        return credentials


__all__ = ['MySQLFetcher', ]
