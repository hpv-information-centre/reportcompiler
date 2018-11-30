""" Module for installing module as pip package """
import os
from setuptools import find_packages, setup
import sys

sys.path.insert(0, os.path.abspath(__file__))
from reportcompiler import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

os.chdir(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='reportcompiler',
    version=__version__,
    packages=find_packages('.'),
    include_package_data=True,
    license='GPL-3.0 License',
    description='Report Compiler generates documents with information'
                ' specified by a document specification (see documentation)',
    long_description=README,
    url='https://www.hpvcentre.net',
    author='David Gómez',
    author_email='info@hpvcenter.net',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    install_requires=[
        'pandas>=0.22.0',
        'anytree>=2.4.3',
        'jsmin>=2.2.2',
        'GitPython>=2.1.9',
        'odictliteral>=1.0.0',
        'sphinx-autoapi>=0.5.0',
        'setuptools>=39.2.0',
        'sphinx>=1.7.5',
        'autoapi>=1.3.1',
        'sphinxcontrib-websupport>=1.0.1',
        # Not strictly requirement, but convenient to have as one
        'pymysql>=0.8.1'
    ],
    entry_points={
        'reportcompiler.data_fetchers': [
            'constant=reportcompiler.plugins.data_fetchers.constant:'
            'ConstantFetcher',
            'excel=reportcompiler.plugins.data_fetchers.excel:'
            'ExcelFetcher',
            'mysql=reportcompiler.plugins.data_fetchers.mysql:'
            'MySQLFetcher',
            'sqlite=reportcompiler.plugins.data_fetchers.sqlite:'
            'SQLiteFetcher',
        ],
        'reportcompiler.source_parsers': [
            'python=reportcompiler.plugins.source_parsers.python:'
            'PythonParser',
            'r=reportcompiler.plugins.source_parsers.r:'
            'RParser',
        ],
        'reportcompiler.template_renderers': [
            'jinja2=reportcompiler.plugins.template_renderers.jinja2:'
            'JinjaRenderer',
            'jinja2-latex=reportcompiler.plugins.template_renderers.jinja2:'
            'JinjaLatexRenderer',
            'rmarkdown=reportcompiler.plugins.template_renderers.rmarkdown:'
            'RMarkdownRenderer',
        ],
        'reportcompiler.postprocessors': [
            'pdflatex=reportcompiler.plugins.postprocessors.pdflatex:'
            'PdflatexPostProcessor',
            'pandoc=reportcompiler.plugins.postprocessors.pandoc:'
            'PandocPostProcessor',
            'pandoc-html=reportcompiler.plugins.postprocessors.pandoc:'
            'PandocHTMLPostProcessor',
        ],
        'console_scripts': [
            'compile-report=reportcompiler.command_line:compile_report',
            'compile-fragment=reportcompiler.command_line:compile_fragment'
        ]
    }
)
