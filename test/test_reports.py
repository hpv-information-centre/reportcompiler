import unittest
import os
import shutil
from tempfile import mkdtemp
from reportcompiler.documents import DocumentSpecification


class DocumentsTestCase(unittest.TestCase):
    """ Tests for 'documents.py' """

    @classmethod
    def setUpClass(cls):
        cls.test_tmp_path = mkdtemp()
        cls.test_report = DocumentSpecification(os.path.join(
                                    cls.test_tmp_path,
                                    'test_report'),
                                 create=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_tmp_path)

    def test_init_empty_document(self):
        with self.assertRaises(ValueError):
            DocumentSpecification()

"""
Report
- Invalid directory
- Invalid repository
- Invalid branch in repository

"""
