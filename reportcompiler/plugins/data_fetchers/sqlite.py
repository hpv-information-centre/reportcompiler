""" sqlite.py

This module includes the data fetcher using SQLite.

"""

import os
import sqlite3
import logging
import pandas as pd
from reportcompiler.plugins.data_fetchers.sql \
    import SQLFetcher

__all__ = ['SQLiteFetcher', ]


class SQLiteFetcher(SQLFetcher):
    """ Data fetcher for SQLite databases. """

    def fetch(self, doc_param, fetcher_info, metadata):
        conn = sqlite3.connect(os.path.join(metadata['data_path'],
                                            fetcher_info['file']))
        c = conn.cursor()
        sql_string = self._build_sql_query(doc_param, fetcher_info, metadata)
        logger = logging.getLogger(metadata['logger_name'])
        logger.debug('[{}] {}'.format(metadata['doc_suffix'], sql_string))
        c.execute(sql_string)
        data = c.fetchall()
        column_names = [col[0] for col in c.description]
        df = pd.DataFrame(data=data, columns=column_names)
        return df
