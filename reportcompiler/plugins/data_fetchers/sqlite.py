import os
import sqlite3
import logging
import pandas as pd
from reportcompiler.plugins.data_fetchers.base \
    import DataFetcher
from reportcompiler.plugins.data_fetchers.utils.sql \
    import SQLQueryBuilder


class SQLiteFetcher(DataFetcher):
    """ Data fetcher for SQLite databases. """
    name = 'sqlite'

    def fetch(self, doc_var, fetcher_info, metadata):
        conn = sqlite3.connect(os.path.join(metadata['data_path'],
                                            fetcher_info['file']))
        c = conn.cursor()
        sql_string = SQLQueryBuilder(doc_var, fetcher_info, metadata).build()
        logger = logging.getLogger(metadata['logger_name'])
        logger.debug('[{}] {}'.format(metadata['doc_suffix'], sql_string))
        c.execute(sql_string)
        data = c.fetchall()
        column_names = [col[0] for col in c.description]
        df = pd.DataFrame(data=data, columns=column_names)
        return df


__all__ = ['SQLiteFetcher', ]
