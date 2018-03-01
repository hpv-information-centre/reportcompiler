import unittest
import os
import shutil
from tempfile import mkdtemp
from reportcompiler.reports import Report


class ReportTestCase(unittest.TestCase):
    """ Tests for 'reports.py' """

    @classmethod
    def setUpClass(cls):
        cls.test_tmp_path = mkdtemp()
        cls.test_report = Report(os.path.join(cls.test_tmp_path,
                                              'test_report'),
                                 create=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_tmp_path)

    def test_init_empty_report(self):
        with self.assertRaises(ValueError):
            Report()

"""
Report
- Invalid directory
- Invalid repository
- Invalid branch in repository

"""
