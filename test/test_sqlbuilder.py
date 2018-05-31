import unittest
import os
import shutil
from odictliteral import odict
from tempfile import mkdtemp
from reportcompiler.plugins.errors \
    import DataFetchingError
from reportcompiler.plugins.data_fetchers.utils.sql_builder \
    import SQLQueryBuilder


class SQLBuilderTest(unittest.TestCase):
    """ Tests for SQLQueryBuilder in data_fetchers/sql_fetchers.py """

    test_metadata = {
        'fragment_path': 'sqlbuilder_test'
    }

    def test_simple_query(self):
        fetcher_info = {
            'type': 'mysql',
            'table': 'test_table',
            'fields': ['var1', 'var2']
        }
        expected_query = \
            "SELECT `var1` AS `var1`, `var2` AS `var2` " \
            "FROM test_table"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_distinct_query(self):
        fetcher_info = {
            'type': 'mysql',
            'table': 'test_table',
            'distinct': True,
            'fields': ['var1', 'var2']
        }
        expected_query = \
            "SELECT DISTINCT `var1` AS `var1`, `var2` AS `var2` " \
            "FROM test_table"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_simple_query_alias(self):
        fetcher_info = {
            'type': 'mysql',
            'table': {'test_table': 'tt'},
            'fields': odict['var1': 'v1', 'var2': 'v2']
        }
        expected_query = \
            "SELECT `var1` AS `v1`, `var2` AS `v2` " \
            "FROM `test_table` `tt`"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_simple_query_alias_order(self):
        fetcher_info = {
            'type': 'mysql',
            'table': {'test_table': 'tt'},
            'fields': {'var2': 'v2', 'var1': 'v1'}
        }
        expected_query = \
            "SELECT `var1` AS `v1`, `var2` AS `v2` " \
            "FROM `test_table` `tt`"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_join_query(self):
        fetcher_info = {
            'type': 'mysql',
            'table': {'test_table': 'tt'},
            'fields': {'var1': 'v1'},
            'join': {
                'type': 'inner',
                'table': {'join_table': 'jt'},
                'on': {'tt.id': 'jt.id'}
            }
        }
        expected_query = \
            "SELECT `var1` AS `v1` " \
            "FROM `test_table` `tt` " \
            "INNER JOIN `join_table` `jt` ON `tt`.`id` = `jt`.`id`"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_condition_query(self):
        doc_param = {'iso': 'ESP'}
        fetcher_info = {
            'type': 'mysql',
            'table': {'test_table': 'tt'},
            'fields': {'var1': 'v1'},
            'condition': {'tt.iso': 'iso'},
            'condition_const': {'tt.type': 'country'}
        }
        expected_query = \
            "SELECT `var1` AS `v1` " \
            "FROM `test_table` `tt` " \
            "WHERE `tt`.`iso` IN ('ESP') AND `tt`.`type` IN ('country')"

        query = self._build_expect_ok(fetcher_info, doc_param=doc_param)
        self.assertEqual(query, expected_query)

    def test_group_by_query(self):
        fetcher_info = {
            'type': 'mysql',
            'table': 'test_table',
            'fields': ['var1', 'var2'],
            'group': ['group_var']
        }
        expected_query = \
            "SELECT `var1` AS `var1`, `var2` AS `var2` " \
            "FROM test_table " \
            "GROUP BY `group_var`"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_order_by_query(self):
        fetcher_info = {
            'type': 'mysql',
            'table': 'test_table',
            'fields': ['var1', 'var2'],
            'sort': ['sort_var']
        }
        expected_query = \
            "SELECT `var1` AS `var1`, `var2` AS `var2` " \
            "FROM test_table " \
            "ORDER BY `sort_var` ASC"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_order_by_dict_query(self):
        fetcher_info = {
            'type': 'mysql',
            'table': 'test_table',
            'fields': ['var1', 'var2'],
            'sort': odict['sort_var2': 'ASC', 'sort_var1': 'DESC']
        }
        expected_query = \
            "SELECT `var1` AS `var1`, `var2` AS `var2` " \
            "FROM test_table " \
            "ORDER BY `sort_var1` DESC, `sort_var2` ASC"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_limit_offset_query(self):
        fetcher_info = {
            'type': 'mysql',
            'table': 'test_table',
            'fields': ['var1', 'var2'],
            'limit': 10,
            'offset': 5
        }
        expected_query = \
            "SELECT `var1` AS `var1`, `var2` AS `var2` " \
            "FROM test_table LIMIT 10 OFFSET 5"

        query = self._build_expect_ok(fetcher_info)
        self.assertEqual(query, expected_query)

    def test_wrong_id_name(self):
        fetcher_info = {
            'type': 'mysql',
            'table': 'wrong table',
            'fields': ['var1', 'var2', 'var3']
        }
        self._build_expect_exception(fetcher_info)

    def test_missing_table(self):
        fetcher_info = {
            'type': 'mysql',
            'fields': ['var1', 'var2', 'var3']
        }
        self._build_expect_exception(fetcher_info)

    def test_missing_fields(self):
        fetcher_info = {
            'type': 'mysql',
            'table': 'test_table'
        }
        self._build_expect_exception(fetcher_info)

    def _build_expect_exception(self, fetcher_info, doc_param={}):
        builder = SQLQueryBuilder(doc_param,
                                  fetcher_info,
                                  SQLBuilderTest.test_metadata)
        with self.assertRaises(DataFetchingError):
            builder.build()

    def _build_expect_ok(self, fetcher_info, doc_param={}):
        builder = SQLQueryBuilder(doc_param,
                                  fetcher_info,
                                  SQLBuilderTest.test_metadata)
        return _strip(builder.build())


def _strip(var):
    return ' '.join(var.split()).strip()
