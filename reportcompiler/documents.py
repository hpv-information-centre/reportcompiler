""" documents.py

This module is responsible for the representation and handling of document
specifications.

"""

import json
import logging
import os
import shutil
from collections import OrderedDict

import git
from jsmin import jsmin
from reportcompiler.documentcompilers import DocumentCompiler

__all__ = ['DocumentSpecification', ]


class DocumentSpecification:
    """
    Represents a document specification with its file structure and
    configuration.
    """

    CONFIG_RECOGNIZED_KEYS = {
        'doc_name', 'verbose_name', 'main_template', 'debug',
        'skip_unchanged_fragments', 'random_seed', 'data_fetchers',
        'source_parser', 'template_renderer', 'postprocessors'
    }

    PARAMS_ALLOWED_KEYS = {
        'augmentation', 'allowed_values', 'mandatory', 'default_key'
    }

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
                    "new document specification creation")
            self._create_document_specification(dir_path)

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
        self.path = os.path.abspath(dir_path)
        name = os.path.basename(self.path)
        if not os.path.exists(self.path):
            raise FileNotFoundError(
                "Directory '{}' doesn't exist".format(self.path))

        self.name = name
        self.metadata = self.build_metadata()

        self.allowed_values = self.fetch_allowed_var_values(doc_param={})

        if not os.path.exists('{}/templates/{}'.format(
                self.path,
                self.metadata['main_template'])):
            raise FileNotFoundError(
                "Main template defined in config.conf ({}) doesn't exist".
                format(self.metadata['main_template']))

    def build_metadata(self):
        config_file = '{}/config.conf'.format(self.path)
        if not os.path.exists(config_file):
            raise FileNotFoundError(
                "Document specification {} has no configuration file".format(
                    self.name) +
                " (config.conf)")

        with open(config_file) as config_data:
            metadata = json.loads(jsmin(config_data.read()),
                                  object_pairs_hook=OrderedDict)
            # Additional metadata keys beyond the official ones are allowed for
            # custom functionality

        params_file = '{}/params.conf'.format(self.path)
        if os.path.exists(params_file):
            with open(params_file) as params_data:
                params_config = json.loads(jsmin(params_data.read()),
                                           object_pairs_hook=OrderedDict)
                unknown_keys = set(params_config.keys()) - \
                    DocumentSpecification.PARAMS_ALLOWED_KEYS
                if len(unknown_keys) > 0:
                    raise ValueError("Unknown values found in params.conf: {}".
                                     format(', '.join(unknown_keys)))
                metadata.update({'params': params_config})

        metadata['docspec_path'] = self.path
        metadata['skip_unchanged_fragments'] = \
            metadata.get('skip_unchanged_fragments', True)

        style_file = '{}/style.conf'.format(self.path)
        if os.path.exists(style_file):
            with open(style_file) as style_data:
                style_config = json.loads(jsmin(style_data.read()),
                                          object_pairs_hook=OrderedDict)
                metadata.update({'style': style_config})
                if style_config.get('data_fetchers'):
                    metadata['style'].update(
                        DocumentCompiler.fetch_style_data(metadata))
                    del metadata['style']['data_fetchers']
        return metadata

    def __str__(self):
        return self.metadata.get('verbose_name') or \
            self.metadata['doc_name']

    def _create_document_specification(self, new_docspec_path):
        """
        Creates a new document specification.
        :param str new_docspec_path: Full path of the new document
            specification. The parent path must exist, and the last
            directory in the path will be created.
        """
        if not os.path.exists(
            os.path.normpath(
                os.path.join(new_docspec_path, os.path.pardir))):
            raise EnvironmentError(
                "Parent path for new document specification doesn't exist"
            )
        if os.path.exists(new_docspec_path):
            raise EnvironmentError("Document specification already exists")

        os.mkdir(new_docspec_path)
        dirs = ['src', 'templates', 'data', 'credentials']
        for d in dirs:
            os.mkdir(os.path.join(new_docspec_path, d))
        config_content = """
        {
            "name": "new_report",
            "verbose_name": "New report",
            "main_template": "report.tex",

            "template_renderer": "jinja2-latex",
            "postprocessors": "pdflatex"
        }
        """
        with open(os.path.join(new_docspec_path, 'config.conf'), 'w') \
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
        with open(os.path.join(new_docspec_path, 'params.conf'), 'w') \
                as param_file:
            param_file.write(param_content)

        main_template_content = r"""
        \documentclass[11pt]{article}

        \begin{document}
        This is a sample document. You can customize this document
        specification by editing the templates and source files along
        with the configuration file.

        \end{document}
        """
        with open(os.path.join(new_docspec_path,
                               'templates',
                               'report.tex'), 'w') as main_template_file:
            main_template_file.write(main_template_content)

    def fetch_allowed_var_values(self, doc_param):
        """
        Returns the allowed values for the document variables for the current
        document specification if specified in the configuration file.

        :param OrderedDict doc_param: Document variable to check, necessary
            when checking dependent variables
        :returns: Dictionary with possible values of the variables specified in
            the document specification configuration. Variables dependent on
            others missing from doc_param are returned with value None.
        :rtype: dict
        """
        dt = DocumentCompiler.fetch_allowed_param_values(
                                doc_param, self.metadata)
        allowed_values = {}
        for col in dt.keys():
            data_list = dt[col].values.flatten().tolist()
            if allowed_values.get(col) is None:
                allowed_values[col] = []
            allowed_values[col].extend(data_list)
        return allowed_values

    @property
    def default_docparam_key(self):
        """
        Return the default key of the document parameter
        that will be used if none is specified.

        :returns: default document parameter key
        :rtype: str
        """
        return self.metadata['params'].get('default_key')

    @property
    def main_template(self):
        """
        Returns the main template filename.

        :returns: main template filename
        :rtype: str
        """
        return self.metadata['main_template']

    def generate(self,
                 doc_params=None,
                 n_doc_workers=2,
                 n_frag_workers=2,
                 debug=False,
                 random_seed=None,
                 fragments=None,
                 log_level=logging.DEBUG,
                 **kwargs):
        """
        Generates the documents with document variables doc_params from the
        current document specification.

        :param OrderedDict|list doc_params: Document variables to generate
            documents
        :param int n_doc_workers: Number of concurrent document-generating
            threads
        :param int n_frag_workers: Number of concurrent fragment-generating
            threads (within each document-generating thread)
        :param int random_seed: Seed to initialize any possible
            pseudorandom generators.
        :param str fragments: Fragment(s) to be generated. Setting this
            value generates the document only considering the templates from
            the main template to the chosen value(s) and all its children.
            Setting it to None is equivalent to setting it to the main template
            and therefore the whole document will be generated.
        :param int log_level: Log level (e.g. logging.DEBUG, logging.WARNING,
            logging.ERROR, ...).
        :param dict kwargs: Additional arguments that will be added to the
            document metadata when generating the documents.
        """
        if doc_params is None:
            doc_params = OrderedDict()
        if not isinstance(doc_params, list):
            doc_params = [doc_params]
        for i, doc_param in enumerate(doc_params):
            if self.default_docparam_key:
                if not isinstance(doc_param, dict):
                    doc_params[i] = {self.default_docparam_key: doc_param}
            elif not isinstance(doc_param, dict):
                raise ValueError(
                    'Document parameter is not a dictionary '
                    'and default key is not set')

        doc_params = self._clean_and_validate_doc_params(doc_params)

        metadata = self.metadata.copy()
        metadata.update(kwargs)

        compiler = DocumentCompiler(self)
        results = compiler.generate(doc_params, metadata,
                                    n_doc_workers=n_doc_workers,
                                    n_frag_workers=n_frag_workers,
                                    debug=debug,
                                    random_seed=random_seed,
                                    fragments=fragments,
                                    log_level=log_level)
        return results

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

    def _clean_and_validate_doc_params(self, doc_params):
        """
        Validation and cleaning of input document variable list.

        :param list doc_params: Input document variable list
        :returns: Cleaned up document variable list
        :rtype: list
        """
        DocumentSpecification._check_and_clean_duplicate_variables(doc_params)

        for doc_param in doc_params:
            self._check_mandatory_variables(doc_param)
            self._check_allowed_values(doc_param)

        return doc_params

    @staticmethod
    def _check_and_clean_duplicate_variables(doc_params):
        for doc_param in doc_params:
            num_occurrences = doc_params.count(doc_param)
            if num_occurrences > 1:
                doc_params.remove(doc_param)
                logging.warning(
                    '{} appears more than once, duplicates will be ignored...'.
                    format(doc_param))

    def _check_mandatory_variables(self, doc_param):
        if self.metadata['params'].get('mandatory') is None:
            return
        mandatory_vars = self.metadata['params']['mandatory']
        if mandatory_vars is None:
            mandatory_vars = []
        mandatory_vars = set(mandatory_vars)

        current_var_keys = set(doc_param.keys())
        if not mandatory_vars.issubset(current_var_keys):
            missing_vars = mandatory_vars - current_var_keys
            raise ValueError(
                'Some mandatory document variables were not specified: {}'.
                format(', '.join(missing_vars)))

    # TODO: Fix doc_param dependencies
    def _check_allowed_values(self, doc_param):
        allowed_values = self.fetch_allowed_var_values(doc_param)
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
                                  var in doc_param.keys())}

            allowed_values_errors = [(var, str(doc_param.get(var)), values)
                                     for var, values in allowed_values.items()
                                     if (doc_param.get(var) is not None and
                                         doc_param[var] not in values)]

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
                    if self.metadata['params'].get('allowed_values') is None:
                        dependencies = []
                    else:
                        dependencies = [
                                fetcher['dependencies']
                                for fetcher in self.metadata['params'][
                                    'allowed_values']
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
