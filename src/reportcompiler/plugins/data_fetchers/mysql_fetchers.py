import pymysql.cursors
import pandas as pd
import pymysql
import pymysql.cursors
import os
import json
from threading import Lock
from pymysql.err import OperationalError
from reportcompiler.plugins.data_fetchers.data_fetchers \
    import FragmentDataFetcher


class MySQLFetcher(FragmentDataFetcher):
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
            raise FragmentDataFetcher.raise_data_fetching_exception(
                    metadata['fragment_path'],
                    e,
                    metadata)

        if fetcher_info.get('raw_query'):
            sql_string = fetcher_info['raw_query']
        else:
            try:
                select_clause = MySQLFetcher._create_select_clause(
                                                fetcher_info,
                                                metadata)
                from_clause = MySQLFetcher._create_from_clause(
                                                fetcher_info,
                                                metadata)
                join_clause, select_join_clause = \
                    MySQLFetcher._create_join_clause(
                                    fetcher_info,
                                    metadata)
                if select_join_clause:
                    select_clause = ', '.join([select_clause,
                                               select_join_clause])
                where_clause = MySQLFetcher._create_where_clause(
                                                doc_var,
                                                fetcher_info,
                                                metadata)
            except KeyError:
                raise FragmentDataFetcher.raise_data_fetching_exception(
                    metadata['fragment_path'],
                    None,
                    metadata,
                    message='Table/column definition not defined for fragment')
            sql_string = 'SELECT {} FROM {} {} WHERE {}'.format(
                                                            select_clause,
                                                            from_clause,
                                                            join_clause,
                                                            where_clause)

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
                raise FragmentDataFetcher.raise_data_fetching_exception(
                    metadata['fragment_path'],
                    None,
                    metadata,
                    message='MySQL credentials not specified in context')
        return credentials

    @staticmethod
    def _create_select_clause(context, metadata):
        # Metadata as parameter for possible future options
        column_aliases = context['columns']
        if isinstance(column_aliases, list):
            column_aliases = {c: c for c in column_aliases}
        return ', '.join(['t0.`{}` AS `{}`'.format(col_name, alias)
                          for col_name, alias in column_aliases.items()])

    @staticmethod
    def _create_from_clause(context, metadata):
        # Metadata as parameter for possible future options
        return context['table'] + ' t0'

    @staticmethod
    def _create_join_clause(context, metadata):
        join_info = context.get('join')
        if join_info is None:
            return '', None  # No join clause

        if not isinstance(join_info, list):
            join_info = [join_info]

        try:
            join_list = []
            select_list = []
            for i, join_term in enumerate(join_info):
                join_type = join_term.get('type')
                if join_type is None:
                    join_type = 'INNER'
                join_type = join_type.upper()
                if join_type not in ['INNER', 'OUTER', 'LEFT', 'RIGHT']:
                    raise FragmentDataFetcher.raise_data_fetching_exception(
                        context['fragment_path'],
                        None,
                        metadata,
                        message='Invalid join type: {}'.format(join_type))

                table = join_term['table'] + ' t' + str(i+1)
                on_columns = join_term['on']
                on_columns_str = \
                    ['t{}.`'.format(i+1) + k + '` = t0.`' + v + '`'
                     for k, v in on_columns.items()]
                join_str = '{} JOIN {} ON {}'.format(
                                join_type,
                                table, ' AND '.join(on_columns_str))
                join_list.append(join_str)

                selected_columns = join_term['columns']
                if isinstance(selected_columns, list):
                    selected_columns = {c: c for c in selected_columns}
                selected_columns_str = ', '.join(
                    ['t{}.`{}` AS `{}`'.format(i+1, k, v)
                     for k, v
                     in selected_columns.items()])
                select_list.append(selected_columns_str)
            return ' '.join(join_list), ', '.join(select_list)

        except KeyError:
            raise FragmentDataFetcher.raise_data_fetching_exception(
                context['fragment_path'],
                None,
                metadata,
                message='Missing info in join clause: {}'.format(
                    ', '.join('asd')))

    @staticmethod
    def _create_where_clause(doc_var, context, metadata):
        column_aliases = context['columns']
        if isinstance(column_aliases, list):
            column_aliases = {v: v for v in column_aliases}

        alias_list = list(column_aliases.values())
        duplicated_aliases = set([x
                                  for x
                                  in alias_list if alias_list.count(x) > 1])
        if len(duplicated_aliases) > 0:
            raise FragmentDataFetcher.raise_data_fetching_exception(
                context['fragment_path'],
                None,
                metadata,
                message='Duplicated aliases: {}'.format(
                    ', '.join(duplicated_aliases)))

        if isinstance(column_aliases, list):
            column_keys = set(column_aliases)
        else:
            column_keys = set(column_aliases.keys())

        try:
            column_keys = column_keys.union(set(context['filter'].keys()))
        except KeyError:
            pass  # No filtering by variables

        try:
            column_keys = column_keys.union(
                            set(context['filter_const'].keys()))
        except KeyError:
            pass  # No filtering by constants

        column_aliases = {v: column_aliases[v]
                          if v in column_aliases.keys() else v
                          for v in column_keys}

        filter_clause = []
        filter_clause.extend(MySQLFetcher._build_filter_term(
                                context,
                                column_aliases,
                                doc_var,
                                metadata,
                                is_var=True))
        filter_clause.extend(MySQLFetcher._build_filter_term(
                                context,
                                column_aliases,
                                doc_var,
                                metadata,
                                is_var=False))
        filter_clause = ' AND '.join(filter_clause)
        if filter_clause == '':
            filter_clause = '1'
        return filter_clause

    @staticmethod
    def _build_filter_term(context, column_aliases, doc_var, metadata, is_var):
        if is_var:
            key = 'filter'
        else:
            key = 'filter_const'
        filter_clause = []
        column = None
        try:
            for column, value in context[key].items():
                if is_var:
                    value = doc_var[value]
                if isinstance(value, list):
                    value = ["'" + str(v) + "'" for v in value]
                    filter_value = ','.join(value)
                else:
                    filter_value = "'" + str(value) + "'"
                db_column = [name
                             for name, alias in column_aliases.items()
                             if alias == column or name == column][0]
                column_filter_clause = '`{}` IN ({})'.format(
                                                        db_column,
                                                        filter_value)
                filter_clause.append(column_filter_clause)
        except IndexError:
            raise FragmentDataFetcher.raise_data_fetching_exception(
                context['fragment_path'],
                None,
                metadata,
                message='Filter column name "{}" not in column list'.
                        format(column))
        except KeyError:
            pass  # No filtering necessary
        return filter_clause

__all__ = ['MySQLFetcher', ]
