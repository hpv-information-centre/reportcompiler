""" Module for installing module as pip package """
import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

os.chdir(
    os.path.normpath(
        os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='reportcompiler',
    version='0.3.1',
    packages=find_packages('.'),
    include_package_data=True,
    license='MIT License',
    description='Report Compiler generates documents with information'
                ' specified by a report directory (see documentation)',
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
        'pandas',
        'anytree',
        'jsmin',
        'GitPython',
        'odictliteral',
    ],
    entry_points={
        'reportcompiler.metadata_retrievers': [
            'python=reportcompiler.plugins.metadata_retrievers.python:'
            'PythonMetadataRetriever',
            'r=reportcompiler.plugins.metadata_retrievers.r:'
            'RMetadataRetriever',
        ],
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
        'reportcompiler.context_generators': [
            'python=reportcompiler.plugins.context_generators.python:'
            'PythonContextGenerator',
            'r=reportcompiler.plugins.context_generators.r:'
            'RContextGenerator',
        ],
        'reportcompiler.template_renderers': [
            'jinja=reportcompiler.plugins.template_renderers.jinja2:'
            'JinjaRenderer',
            'jinja-latex=reportcompiler.plugins.template_renderers.jinja2:'
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
    }
)
