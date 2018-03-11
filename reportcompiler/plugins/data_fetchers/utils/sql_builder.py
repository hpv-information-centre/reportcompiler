""" sql_builder.py

This module includes the utilities to build SQL queries from structured
JSON data.

"""

# TODO: Document JSON -> SQL specification
# (inspired by https://github.com/2do2go/json-sql/tree/master/docs#type-select)

# TODO: Consider other condition (WHERE) types (>, <, other builtins, ...)
# TODO: Consider adding subqueries to specification
# TODO: Test and optimize for larger data sets

import re
from collections import OrderedDict
from reportcompiler.plugins.data_fetchers.base \
    import DataFetcher

__all__ = ['SQLQueryBuilder', ]


class SQLQueryBuilder:
    """
    Class responsible of building the SQL query string with the
    JSON specification.
    """
    def __init__(self, doc_var, fetcher_info, metadata):
        self.doc_var = doc_var
        self.fetcher_info = fetcher_info
        self.metadata = metadata

    def build(self):
        """
        Builds the SQL query string with the JSON specification provided
            in the constructor.
        :returns: SQL query string
        :rtype: str
        """
        if self.fetcher_info.get('raw_query'):
            sql_string = self.fetcher_info['raw_query']
        else:
            select_clause = self._create_select_clause()
            from_clause = self._create_from_clause()
            join_clause = self._create_join_clause()
            where_clause = self._create_where_clause()
            group_by_clause = self._create_group_by_clause()
            order_by_clause = self._create_sort_clause()
            limit_clause = self._create_limit_clause()

            sql_string = """
                            {select_clause}
                            {from_clause}
                            {join_clause}
                            {where_clause}
                            {group_by_clause}
                            {order_by_clause}
                            {limit_clause}
                        """.format(
                                select_clause=select_clause,
                                from_clause=from_clause,
                                join_clause=join_clause,
                                where_clause=where_clause,
                                group_by_clause=group_by_clause,
                                order_by_clause=order_by_clause,
                                limit_clause=limit_clause)
        return ' '.join(sql_string.split())

    def _create_select_clause(self):
        if self.fetcher_info.get('fields') is None:
            self._raise_exception("'fields' field missing")
        column_aliases = self.fetcher_info['fields']
        if isinstance(column_aliases, list):
            column_aliases = OrderedDict([(c, c) for c in column_aliases])
        alias_list = ['`{}` AS `{}`'.format(col_name.replace('.', '`.`'),
                                            alias)
                      for col_name, alias in column_aliases.items()]

        select_clause = ', '.join(alias_list)
        if self.fetcher_info.get('distinct') is None:
            distinct = False
        else:
            distinct = self.fetcher_info['distinct']
        if distinct:
            select_clause = 'DISTINCT {}'.format(select_clause)

        return 'SELECT ' + select_clause

    def _create_from_clause(self):
        if self.fetcher_info.get('table') is None:
            self._raise_exception("'table' field missing")
        if isinstance(self.fetcher_info['table'], dict):
            if len(self.fetcher_info['table']) != 1:
                self._raise_exception(
                        '"table" field must have exactly one element')
            table_item = list(self.fetcher_info['table'].items())[0]
            self._validate_sql_varname(list(table_item))
            from_clause = '`{}` `{}`'.format(table_item[0], table_item[1])
        elif isinstance(self.fetcher_info['table'], str):
            self._validate_sql_varname(self.fetcher_info['table'])
            from_clause = self.fetcher_info['table']
        else:
            self._raise_exception(
                    '"table" field must be either a str or a dict')
        return 'FROM ' + from_clause

    def _create_join_clause(self):
        join_info = self.fetcher_info.get('join')
        if join_info is None:
            return ''

        if not isinstance(join_info, list):
            join_info = [join_info]

        try:
            join_list = []
            for join_term in join_info:
                join_type = join_term.get('type')
                if join_type is None:
                    join_type = 'INNER'
                join_type = join_type.upper()
                if join_type not in ['INNER', 'OUTER', 'LEFT', 'RIGHT']:
                    self._raise_exception(
                            'Invalid join type: {}'.format(join_type))

                if isinstance(join_term['table'], dict):
                    if len(join_term['table']) != 1:
                        self._raise_exception("join 'table' field must "
                                              "have exactly one element")
                    table_pair = list(join_term['table'].items())[0]
                    self._validate_sql_varname([table_pair[0], table_pair[1]])
                    table = '`{}` `{}`'.format(table_pair[0], table_pair[1])
                elif isinstance(join_term['table'], str):
                    self._validate_sql_varname(join_term['table'])
                    table = join_term['table']
                else:
                    self._raise_exception("join 'table' field must "
                                          "be either a str or a dict")

                on_columns = join_term['on']
                self._validate_sql_varname(
                    [val1 for val1, _ in join_term['on'].items()])
                self._validate_sql_varname(
                    [val2 for _, val2 in join_term['on'].items()])
                on_columns_str = ['`{}` = `{}`'.format(k.replace('.', '`.`'),
                                                       v.replace('.', '`.`'))
                                  for k, v in on_columns.items()]

                join_str = '{} JOIN {} ON {}'.format(
                                join_type,
                                table, ' AND '.join(on_columns_str))
                join_list.append(join_str)
            return ' '.join(join_list)
        except KeyError:
            self._raise_exception('Missing info in join clause')

    def _create_where_clause(self):
        column_aliases = self.fetcher_info['fields']
        if isinstance(column_aliases, list):
            column_aliases = {v: v for v in column_aliases}
        self._validate_sql_varname(
            [name for name, alias in column_aliases.items()])
        self._validate_sql_varname(
            [alias for name, alias in column_aliases.items()])

        filter_clause = []
        filter_clause.extend(
            self._build_filter_term(is_var=True))
        filter_clause.extend(
            self._build_filter_term(is_var=False))

        filter_clause = ' AND '.join(filter_clause)
        if filter_clause != '':
            filter_clause = 'WHERE {}'.format(filter_clause)
        return filter_clause

    def _build_filter_term(self, is_var):
        if is_var:
            key = 'condition'
        else:
            key = 'condition_const'
        filter_clause = []
        column = None
        try:
            for column, value in self.fetcher_info[key].items():
                self._validate_sql_varname(column)
                # self._validate_sql_varname(value)
                if is_var:
                    if not isinstance(value, list):
                        value = [value]
                    for i, v in enumerate(value):
                        try:
                            value[i] = self.doc_var[v]
                        except KeyError:
                            self._raise_exception(
                                    'Variable "{}" used in fetcher '
                                    '"condition" field is not available in '
                                    'doc_var'
                                    .format(v))
                if isinstance(value, list):
                    value = ["'" + str(v) + "'" for v in value]
                    filter_value = ','.join(value)
                else:
                    filter_value = "'" + str(value) + "'"
                column_filter_clause = '`{}` IN ({})'.format(
                                                    column.replace('.', '`.`'),
                                                    filter_value)
                filter_clause.append(column_filter_clause)
        except IndexError:
            self._raise_exception(
                    'Condition field name "{}" not in column list'
                    .format(column))
        except KeyError:
            pass
        return filter_clause

    def _create_group_by_clause(self):
        if not self.fetcher_info.get('group'):
            return ''

        self._validate_sql_varname(self.fetcher_info['group'])
        return 'GROUP BY {}'.format(', '.join(
            ['`{}`'.format(v.replace('.', '`.`'))
             for v
             in self.fetcher_info['group']]))

    def _create_sort_clause(self):
        if not self.fetcher_info.get('sort'):
            return ''
        sort_vars = self.fetcher_info['sort']
        if isinstance(sort_vars, list):
            sort_vars = {v: 'ASC' for v in sort_vars}
        elif not isinstance(sort_vars, dict):
            self._raise_exception(
                "'sort' values must either be a list or a dict")

        self._validate_sql_varname([var for var, sort in sort_vars.items()])
        sort_values = ['`{}` {}'.format(var.replace('.', '`.`'), sort)
                       for var, sort
                       in sort_vars.items()]
        sort_values.sort()
        return 'ORDER BY {}'.format(', '.join(sort_values))

    def _create_limit_clause(self):
        if not self.fetcher_info.get('limit'):
            return ''
        if not isinstance(self.fetcher_info['limit'], int):
            self._raise_exception("'limit' field must be numeric")
        offset_clause = self._create_offset_clause()
        return 'LIMIT {} {}'.format(self.fetcher_info['limit'], offset_clause)

    def _create_offset_clause(self):
        if not self.fetcher_info.get('offset'):
            return ''
        if not isinstance(self.fetcher_info['offset'], int):
            self._raise_exception("'limit' field must be numeric")
        return 'OFFSET {}'.format(self.fetcher_info['offset'])

    def _validate_sql_varname(self, var):
        """
        Raises exception if 'name' is not a valid field/table identifier (i.e.
        a word or two words separated by a dot). Accepts single variables or
        lists.
        """
        if isinstance(var, str):
            var = [var]
        elif not isinstance(var, list):
            self._raise_exception('Field/table name not valid')

        for name in var:
            if not isinstance(name, str):
                self._raise_exception('Expected string value for identifier')
            match1 = re.fullmatch(r'\w*', name)
            match2 = re.fullmatch(r'\w*\.\w*', name)
            if match1 is None and match2 is None:
                self._raise_exception(
                    "'{}' is not a valid field/table identifier"
                    .format(name))

    def _raise_exception(self, message):
        raise DataFetcher.raise_data_fetching_exception(
            self.metadata,
            message=message)
