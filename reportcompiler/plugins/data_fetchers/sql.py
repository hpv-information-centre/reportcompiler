""" sql.py

This module includes the base data fetcher class using SQL.

"""


from reportcompiler.plugins.data_fetchers.base \
    import DataFetcher
from reportcompiler.plugins.data_fetchers.utils.sql_builder \
    import SQLQueryBuilder


class SQLFetcher(DataFetcher):
    """
    (Abstract) data fetcher for MySQL databases. It extracts the
    common methods to handle any kind of SQL dialects (mysql, sqlite,...)
    """
    name = 'sql'

    def _build_sql_query(self, doc_var, fetcher_info, metadata):
        return SQLQueryBuilder(doc_var,
                               fetcher_info,
                               metadata).build()


__all__ = ['SQLFetcher', ]
