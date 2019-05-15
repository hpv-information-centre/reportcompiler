""" mysql.py

This module includes the data fetcher using MySQL.

"""

import os
import json
import threading
import pandas as pd
from reportcompiler.credential_manager import CredentialManager
from reportcompiler.plugins.data_fetchers.base \
    import DataFetcher
from reportcompiler.plugins.data_fetchers.sql \
    import SQLFetcher

try:
    import pymysql.cursors
    import pymysql
    from pymysql.err import OperationalError
except ImportError:
    print('Python package "pymysql" needed for mysql data fetcher. '
          'This module will not work without it.')

__all__ = ['MySQLFetcher', ]


class MySQLFetcher(SQLFetcher):
    """ Data fetcher for MySQL databases. """
    mutex = threading.Lock()

    class DatabaseConnection:
        def __init__(self, credentials, metadata):
            self.credentials = credentials
            self.metadata = metadata

        def __enter__(self):
            self.connection = pymysql.connect(
                            host=self.credentials['host'],
                            user=self.credentials['user'],
                            password=self.credentials['password'],
                            db=self.credentials['db'],
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
            return self.connection

        def __exit__(self, type, value, traceback):
            if type is None:
                self.connection.close()

    def fetch(self, doc_param, fetcher_info, metadata):
        # TODO: Look for ways to avoid mutex
        with MySQLFetcher.mutex:
            data = self._fetch(doc_param, fetcher_info, metadata)
        return data

    def _fetch(self, doc_param, fetcher_info, metadata):
        credentials = MySQLFetcher._create_context_credentials(fetcher_info,
                                                               metadata)
        try:
            with MySQLFetcher.DatabaseConnection(credentials, metadata) \
                    as connection:
                try:
                    sql_string = self._build_sql_query(doc_param,
                                                       fetcher_info,
                                                       metadata)
                except KeyError:
                    raise DataFetcher.raise_data_fetching_exception(
                        metadata,
                        message='Table/column definition not '
                                'defined for fragment')

                df = pd.read_sql(sql_string, con=connection)
                return df
        except OperationalError as e:
            raise DataFetcher.raise_data_fetching_exception(
                    metadata,
                    exception=e)

    @staticmethod
    def _create_context_credentials(fetcher_info, metadata):
        credentials = None

        try:
            with open(os.path.join(metadata['docspec_path'],
                                   'credentials',
                                   fetcher_info['credentials_file']),
                      'r') as cred_file:
                credentials = json.load(cred_file)
        except KeyError:
            pass  # No credentials file specified
        except Exception as e:
            raise DataFetcher.raise_data_fetching_exception(
                metadata,
                message='MySQL credentials {} don\'t exist'.format(
                    fetcher_info['credentials_file']))

        if credentials is None:
            try:
                credentials = CredentialManager.retrieve(
                                fetcher_info['credentials'])
            except KeyError:
                pass  # No credentials specified

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
                    message='MySQL credentials not specified')
        return credentials
