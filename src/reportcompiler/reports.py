import json
import logging
import os
import sys
import traceback
from collections import ChainMap, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from glob import glob

import git
import pandas as pd
from anytree import RenderTree as Tree
from anytree import Node, PreOrderIter
from git import InvalidGitRepositoryError
from jsmin import jsmin
from reportcompiler.reportcompilers import ReportCompiler


class Report:
    """Represents a report with its file structure and configuration."""
    def __init__(self, directory=None, repo_url=None, repo_path=None):
        if directory is None and repo_url is None:
            raise ValueError("'directory' or 'repo' must be specified")
        if repo_url:
            if repo_path is None:
                raise ValueError(
                    'Local path to store repository must be specified')
            repo_name, _ = os.path.splitext(os.path.basename(repo_url))
            repo_path = os.path.join(repo_path, repo_name)
            if not os.path.exists(repo_path):
                os.mkdir(repo_path)
            try:
                git.Repo(repo_path)
            except InvalidGitRepositoryError:
                repo = git.Repo.init(repo_path)
                repo.create_remote('origin', repo_url)
                repo.remotes.origin.pull('master')
            directory = repo_path
        name = os.path.basename(directory)
        config_file = '{}/config.json'.format(directory)
        if not os.path.exists(config_file):
            raise FileNotFoundError(
                "Report doesn't exist or has no configuration file"
                " (config.json)")

        with open(config_file) as config_data:
            config = json.loads(jsmin(config_data.read()))
        self.name = name
        self.path = directory
        self.metadata = OrderedDict(config)
        self.metadata['report_path'] = self.path

        self.allowed_values = self.fetch_allowed_var_values(doc_var={})

        if not os.path.exists('{}/templates/{}'.format(
                self.path,
                self.metadata['main_template'])):
            raise FileNotFoundError(
                "Main template defined in config.ini ({}) doesn't exist".
                format(self.metadata['main_template']))

    def __str__(self):
        return self.metadata.get('verbose_name') or self.metadata['name']

    def fetch_allowed_var_values(self, doc_var):
        """
        Returns the allowed values for the document variables for the current
        report if specified in the configuration file.
        :param doc_var: Document variable to check, necessary when checking
        dependent variables
        :return: Dictionary with possible values of the variables specified in
        the report configuration. Variables dependent on others missing from
        doc_var are returned with value None.
        """
        # allowed_values = None
        # doc_var_keys = doc_var.keys()
        # if self.metadata.get('allowed_docvar_values_fetcher') is not None:
        #     doc_var_values_fetchers = self.metadata[
        #                                 'allowed_docvar_values_fetcher']
        #     if isinstance(doc_var_values_fetchers, dict):
        #         doc_var_values_fetchers = [doc_var_values_fetchers]
        #     allowed_values = {}

        #     for fetcher_info in doc_var_values_fetchers:
        #         if (fetcher_info.get('dependencies') and
        #                 not set(fetcher_info['dependencies']).issubset(
        #                         set(doc_var_keys))):
        #             allowed_values[fetcher_info['name']] = []
        #             continue
        #         fetcher = FragmentDataFetcher.get(id=fetcher_info)
        #         dt = fetcher.fetch(doc_var, fetcher_info, self.metadata)
        #         for col in dt.columns:
        #             if allowed_values.get(col) is None:
        #                 allowed_values[col] = []
        #             allowed_values[col].extend(list(dt[col]))
        # return allowed_values
        try:
            dt = ReportCompiler.fetch_info(doc_var, self.metadata)
        except NotImplementedError:
            return None
        allowed_values = {}
        for col in dt.keys():
            data_list = dt[col].values.flatten().tolist()
            if allowed_values.get(col) is None:
                allowed_values[col] = []
            allowed_values[col].extend(data_list)
        return allowed_values

    @property
    def main_template(self):
        """
        Returns the main template filename
        :return: main template filename
        """
        return self.metadata['main_template']

    def generate(self,
                 doc_vars=None,
                 n_doc_workers=2,
                 n_frag_workers=2,
                 debug_level=logging.DEBUG):
        """
        Generates the documents with document variables doc_vars from the
        current report.
        :param doc_vars: Document variables to generate documents
        :param n_doc_workers: Number of concurrent document-generating threads
        :param n_frag_workers: Number of concurrent fragment-generating
        threads (within each document-generating thread)
        :param debug_level: Debug level (e.g. logging.DEBUG, logging.WARNING,
        logging.ERROR, ...)
        """
        if doc_vars is None:
            doc_vars = {}
        if not isinstance(doc_vars, list):
            doc_vars = [doc_vars]

        doc_vars = self._clean_and_validate_doc_vars(doc_vars)

        compiler = ReportCompiler(self)
        compiler.generate(doc_vars, self.metadata,
                          n_doc_workers=n_doc_workers,
                          n_frag_workers=n_frag_workers,
                          debug_level=debug_level)

    def _clean_and_validate_doc_vars(self, doc_vars):
        """
        Validation and cleaning of input document variable list
        :param doc_vars: Input document variable list
        :return: Cleaned up document variable list
        """
        Report._check_and_clean_duplicate_variables(doc_vars)

        for doc_var in doc_vars:
            self._check_mandatory_variables(doc_var)
            self._check_allowed_values(doc_var)

        return doc_vars

    @staticmethod
    def _check_and_clean_duplicate_variables(doc_vars):
        for doc_var in doc_vars:
            num_occurrences = doc_vars.count(doc_var)
            if num_occurrences > 1:
                doc_vars.remove(doc_var)
                logging.warning(
                    '{} appears more than once, duplicates will be ignored...'.
                    format(doc_var))

    def _check_mandatory_variables(self, doc_var):
        mandatory_vars = self.metadata.get('mandatory_doc_vars')
        if mandatory_vars is None:
            mandatory_vars = []
        mandatory_vars = set(mandatory_vars)

        current_var_keys = set(doc_var.keys())
        if not mandatory_vars.issubset(current_var_keys):
            missing_vars = mandatory_vars - current_var_keys
            raise ValueError(
                'Some mandatory document variables were not specified: {}'.
                format(', '.join(missing_vars)))

    def _check_allowed_values(self, doc_var):
        allowed_values = self.fetch_allowed_var_values(doc_var)
        if allowed_values is not None:
            allowed_values_msg = ' Allowed values for variable "{}" are {}'
            dependent_allowed_values_msg = \
                ' Variable "{}" allowed values depend on "{}"'
            # Missing mandatory variables not appearing in the allowed_values
            # dictionary are dependent on other variables
            dependent_missing_vars = [var for var, values
                                      in allowed_values.items()
                                      if values == []]
            allowed_values = {var: values
                              for var, values in allowed_values.items()
                              if (var not in dependent_missing_vars or
                                  var in doc_var.keys())}

            # TODO: Refactor
            error_msgs = [
                        allowed_values_msg.format(var, ', '.join(
                            allowed_values[var]))
                        if var not in dependent_missing_vars
                        else dependent_allowed_values_msg.format(
                            var,
                            ', '.join(
                                [
                                    fetcher['dependencies']
                                    for fetcher in self.metadata[
                                        'allowed_docvar_values_fetcher']
                                    if fetcher['name'] == var
                                ][0]))
                        for var, values in allowed_values.items()
                        if (doc_var.get(var) is not None and
                            doc_var[var] not in values)]

            if len(error_msgs) > 0:
                allowed_values_msg = '\n'.join(error_msgs)
                raise ValueError(
                    'Some document variables have invalid values.\n{}'.
                    format(allowed_values_msg))

__all__ = ['Report', ]