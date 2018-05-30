""" reports.py

This module is responsible for the representation and handling of report
specifications.

"""

import json
import logging
import os
import shutil
from collections import OrderedDict

import git
from jsmin import jsmin
from reportcompiler.reportcompilers import ReportCompiler

__all__ = ['Report', ]


class Report:
    """Represents a report with its file structure and configuration."""
    def __init__(self,
                 dir_path=None,
                 repo_url=None,
                 repo_branch='master',
                 repo_relative_path='.',
                 create=False):
        if create:
            if repo_url:
                raise ValueError(
                    "Repository info can't be specified on "
                    "new report directory creation")
            self._create_report_specification(dir_path)

        if dir_path is None and repo_url is None:
            raise ValueError("'dir_path' or 'repo' must be specified")
        if repo_url:
            if dir_path is None:
                raise ValueError(
                    'Local path to store repository must be specified')
            repo_name, _ = os.path.splitext(os.path.basename(repo_url))
            dir_path = os.path.join(dir_path, repo_name)
            if not os.path.exists(dir_path):
                os.mkdir(dir_path)
            try:
                git.Repo(dir_path)
            except git.InvalidGitRepositoryError:
                repo = git.Repo.init(dir_path)
                repo.create_remote('origin', repo_url)
                repo.remotes.origin.pull(repo_branch)
            dir_path = os.path.join(dir_path, repo_relative_path)
        self.path = dir_path
        name = os.path.basename(self.path)
        if not os.path.exists(self.path):
            raise FileNotFoundError(
                "Directory '{}' doesn't exist".format(self.path))

        self.name = name
        self.metadata = self.build_metadata()

        self.allowed_values = self.fetch_allowed_var_values(doc_var={})

        if not os.path.exists('{}/templates/{}'.format(
                self.path,
                self.metadata['main_template'])):
            raise FileNotFoundError(
                "Main template defined in config.ini ({}) doesn't exist".
                format(self.metadata['main_template']))

    def build_metadata(self):
        config_file = '{}/config.json'.format(self.path)
        if not os.path.exists(config_file):
            raise FileNotFoundError(
                "Report {} has no configuration file".format(name) +
                " (config.json)")

        with open(config_file) as config_data:
            metadata = json.loads(jsmin(config_data.read()),
                                  object_pairs_hook=OrderedDict)

        params_file = '{}/params.json'.format(self.path)
        if os.path.exists(params_file):
            with open(params_file) as params_data:
                metadata.update(
                    json.loads(jsmin(params_data.read()),
                               object_pairs_hook=OrderedDict)
                )

        metadata['report_path'] = self.path
        metadata['skip_unchanged_fragments'] = \
            metadata.get('skip_unchanged_fragments', True)
        return metadata

    def __str__(self):
        return self.metadata.get('verbose_name') or \
            self.metadata['report_name']

    def _create_report_specification(self, new_report_path):
        """
        Creates a new report specification.
        :param str new_report_path: Full path of the new report specification.
            The parent path must exist, and the last directory in the path will
            be created.
        """
        if not os.path.exists(
            os.path.normpath(
                os.path.join(new_report_path, os.path.pardir))):
            raise EnvironmentError(
                "Parent path for new report doesn't exist"
            )
        if os.path.exists(new_report_path):
            # Report directory already exists, assume report specification
            # exists
            return

        os.mkdir(new_report_path)
        dirs = ['src', 'templates', 'data', 'credentials']
        for d in dirs:
            os.mkdir(os.path.join(new_report_path, d))
        config_content = """
        {
            /* Mandatory settings */
            "name": "new_report",
            "verbose_name": "New report",
            "main_template": "report.tex",

            /* Workflow settings */
            "template_renderer": "jinja-latex",
            "postprocessor": "pdflatex"
        }
        """
        with open(os.path.join(new_report_path, 'config.json'), 'w') \
                as config_file:
            config_file.write(config_content)

        param_content = """
        {
            // This parameters are parsed with data fetchers

            /*
            "name": "param",
            "values": ["val1", "val2", "val3"]
            */
        }
        """
        with open(os.path.join(new_report_path, 'params.json'), 'w') \
                as param_file:
            param_file.write(param_content)

        main_template_content = r"""
        \documentclass[11pt]{article}

        \begin{document}
        This is a sample document. You can customize this report by editing
        the templates and source files along with the configuration file.
        \end{document}
        """
        with open(os.path.join(new_report_path,
                               'templates',
                               'report.tex'), 'w') as main_template_file:
            main_template_file.write(main_template_content)

    def fetch_allowed_var_values(self, doc_var):
        """
        Returns the allowed values for the document variables for the current
        report if specified in the configuration file.

        :param OrderedDict doc_var: Document variable to check, necessary when
            checking dependent variables
        :returns: Dictionary with possible values of the variables specified in
            the report configuration. Variables dependent on others missing
            from doc_var are returned with value None.
        :rtype: dict
        """
        dt = ReportCompiler.fetch_allowed_param_values(doc_var, self.metadata)
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
        Returns the main template filename.

        :returns: main template filename
        :rtype: str
        """
        return self.metadata['main_template']

    def generate(self,
                 doc_vars=None,
                 n_doc_workers=2,
                 n_frag_workers=2,
                 debug_mode=False,
                 log_level=logging.DEBUG):
        """
        Generates the documents with document variables doc_vars from the
        current report.

        :param OrderedDict|list doc_vars: Document variables to generate
            documents
        :param int n_doc_workers: Number of concurrent document-generating
            threads
        :param int n_frag_workers: Number of concurrent fragment-generating
            threads (within each document-generating thread)
        :param int log_level: Log level (e.g. logging.DEBUG, logging.WARNING,
            logging.ERROR, ...)
        """
        if doc_vars is None:
            doc_vars = OrderedDict()
        if not isinstance(doc_vars, list):
            doc_vars = [doc_vars]

        doc_vars = self._clean_and_validate_doc_vars(doc_vars)

        compiler = ReportCompiler(self)
        compiler.generate(doc_vars, self.metadata,
                          n_doc_workers=n_doc_workers,
                          n_frag_workers=n_frag_workers,
                          debug_mode=debug_mode,
                          log_level=log_level)

    def clean(self, docs='all', keep=[]):
        if docs == 'all':
            docs = os.listdir(os.path.join(self.path, 'gen'))
        if not isinstance(docs, list):
            raise ValueError('docs must be a list')
        for doc_dir in os.listdir(os.path.join(self.path, 'gen')):
            if doc_dir in docs and doc_dir not in keep:
                shutil.rmtree(os.path.join(self.path, 'gen', doc_dir))
        if len(os.listdir(os.path.join(self.path, 'gen'))) == 0:
            shutil.rmtree(os.path.join(self.path, 'gen'))

    def _clean_and_validate_doc_vars(self, doc_vars):
        """
        Validation and cleaning of input document variable list.

        :param list doc_vars: Input document variable list
        :returns: Cleaned up document variable list
        :rtype: list
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
        if self.metadata.get('params_mandatory') is None:
            return
        mandatory_vars = self.metadata['params_mandatory']
        if mandatory_vars is None:
            mandatory_vars = []
        mandatory_vars = set(mandatory_vars)

        current_var_keys = set(doc_var.keys())
        if not mandatory_vars.issubset(current_var_keys):
            missing_vars = mandatory_vars - current_var_keys
            raise ValueError(
                'Some mandatory document variables were not specified: {}'.
                format(', '.join(missing_vars)))

    # TODO: Fix doc_var dependencies
    def _check_allowed_values(self, doc_var):
        allowed_values = self.fetch_allowed_var_values(doc_var)
        if allowed_values is not None:
            allowed_values_msg = \
                ' Allowed values for variable "{}" are {}: got {}'
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

            allowed_values_errors = [(var, str(doc_var.get(var)), values)
                                     for var, values in allowed_values.items()
                                     if (doc_var.get(var) is not None and
                                         doc_var[var] not in values)]

            error_msgs = []
            for var, defined_value, values in allowed_values_errors:
                if var not in dependent_missing_vars:
                    MAX_VALUES_DISPLAYED = 30
                    if len(allowed_values[var]) < MAX_VALUES_DISPLAYED:
                        list_values = ', '.join(
                            [str(val)
                                if not isinstance(val, str)
                                else "'" + val + "'"
                                for val
                                in allowed_values[var]]
                        )
                    else:
                        list_values = ', '.join(
                            [str(val)
                                if not isinstance(val, str)
                                else "'" + val + "'"
                                for val
                                in allowed_values[var][:MAX_VALUES_DISPLAYED]]
                        ) + ', ...'
                    msg = allowed_values_msg.format(
                                var,
                                list_values,
                                defined_value
                                if not isinstance(defined_value, str)
                                else "'" + defined_value + "'"
                            )
                else:
                    if self.metadata.get('params_allowed_values') is None:
                        dependencies = []
                    else:
                        dependencies = [
                                fetcher['dependencies']
                                for fetcher in self.metadata[
                                    'params_allowed_values']
                                if fetcher['name'] == var
                        ][0]  # Dependencies of the first (and only) fetcher
                    msg = dependent_allowed_values_msg.format(
                            var,
                            ', '.join(dependencies))
                error_msgs.append(msg)

            if len(error_msgs) > 0:
                allowed_values_msg = '\n'.join(error_msgs)
                raise ValueError(
                    'Some document variables have invalid values.\n{}'.
                    format(allowed_values_msg))
