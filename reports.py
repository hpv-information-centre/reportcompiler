import json
import os
import sys
import logging
import git
import pandas as pd
import traceback
from collections import OrderedDict
from glob import glob
from datetime import datetime
from jsmin import jsmin
from copy import deepcopy
from collections import ChainMap
from git import InvalidGitRepositoryError
from anytree import PreOrderIter, Node, RenderTree as Tree
from concurrent.futures import ThreadPoolExecutor
from reportcompiler.plugins.data_fetchers.data_fetchers import FragmentDataFetcher
from reportcompiler.plugins.context_generators.context_generators import FragmentContextGenerator
from reportcompiler.plugins.metadata_retriever.metadata_retriever import FragmentMetadataRetriever
from reportcompiler.plugins.template_renderers.template_renderers import TemplateRenderer
from reportcompiler.plugins.postprocessors.postprocessors import PostProcessor
from reportcompiler.errors import FragmentGenerationError


class Report:
    """Represents a report with its file structure and configuration."""
    def __init__(self, directory=None, repo_url=None, repo_path=None):
        if directory is None and repo_url is None:
            raise ValueError("'directory' or 'repo' must be specified")
        if repo_url:
            if repo_path is None:
                raise ValueError('Local path to store repository must be specified')
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
            raise FileNotFoundError("Report doesn't exist or has no configuration file (config.json)")

        with open(config_file) as config_data:
            config = json.loads(jsmin(config_data.read()))
        self.name = name
        self.path = directory
        self.config = config

        # source = set([os.path.splitext(s)[0] for s in self.source_code])
        # templates = set([os.path.splitext(t)[0] for t in self.templates])
        # dangling_sources = source.difference(templates)
        # dangling_sources = dangling_sources.difference([s for s in dangling_sources if s.startswith('__')])
        # if len(dangling_sources) > 0:
        # 	print("Warning: some source files don't have corresponding templates: {}".format(
        #         ', '.join(dangling_sources)))
        # dangling_templates = templates.difference(source)
        # if len(dangling_templates) > 0:
        # 	print("Warning: some templates don't have corresponding source files: {}".format(
        #         ', '.join(dangling_templates)))

        if not os.path.exists('{}/templates/{}'.format(self.path, self.config['main_template'])):
            raise FileNotFoundError("Main template defined in config.ini ({}) doesn't exist".format(
                self.config['main_template']))

    def __str__(self):
        return self.config.get('verbose_name') or self.config['name']

    @property
    def main_template(self):
        """
        Returns the main template filename
        :return: main template filename
        """
        return self.config['main_template']

    def generate(self, doc_vars=None, n_doc_workers=2, n_frag_workers=2, debug_level=logging.DEBUG):
        """
        Generates the documents with document variables doc_vars from the current report.
        :param doc_vars: Document variables to generate documents
        :param n_doc_workers: Number of concurrent document-generating threads
        :param n_frag_workers: Number of concurrent fragment-generating threads (within each document-generating thread)
        :param debug_level: Debug level (e.g. logging.DEBUG, logging.WARNING, logging.ERROR, ...)
        """
        if doc_vars is None:
            doc_vars = {}
        if not isinstance(doc_vars, list):
            doc_vars = [doc_vars]
        doc_vars = self._cleanup_doc_vars(doc_vars)

        report_metadata = OrderedDict(self.config)
        report_metadata['report_path'] = self.path
        compiler = ReportCompiler(self)
        compiler.generate(doc_vars, report_metadata, n_doc_workers=n_doc_workers,
                          n_frag_workers=n_frag_workers, debug_level=debug_level)

    def _cleanup_doc_vars(self, doc_vars):
        """
        Validation and cleaning of input document variable list
        :param doc_vars: Input document variable list
        :return: Cleaned up document variable list
        """
        # TODO: Further validation (e.g. limit values, like ISOs, ...)
        mandatory_vars = self.config.get('mandatory_doc_vars')
        if mandatory_vars is None:
            mandatory_vars = []
        mandatory_vars = set(mandatory_vars)

        doc_vars_list = []
        for item in doc_vars:
            num_occurrences = doc_vars.count(item)
            if num_occurrences > 1 and item not in doc_vars_list:
                doc_vars.remove(item)
                logging.warning('{} appears more than once, duplicates will be ignored...'.format(item))

        for doc_var in doc_vars:
            current_var_keys = set(doc_var.keys())
            if not mandatory_vars.issubset(current_var_keys):
                missing_vars = mandatory_vars - current_var_keys
                raise ValueError('Some mandatory document variables were not specified: {}\nVariables set: {}'.format(
                    ', '.join(missing_vars), doc_var))

        return doc_vars


class ReportCompiler:
    """ Class responsible for compiling a report into a document """
    LOG_FORMAT = '%(asctime)-15s %(message)s'

    @staticmethod
    def get_doc_var_suffix(doc_var):
        """
        Generates a unique suffix given a particular document variable
        :param doc_var: Document variable
        :return: String with a representation of the document variable, to be used as a filename suffix
        """
        try:
            if isinstance(doc_var, list) or isinstance(doc_var, tuple):
                suffix = '-'.join([str(v) for v in doc_var])
            elif isinstance(doc_var, dict):
                suffix = '-'.join([str(v) for v in list(doc_var.values())])
            elif isinstance(doc_var, str):
                suffix = doc_var
            else:
                raise ValueError('doc_var has invalid type')
            return suffix
        except KeyError:
            return ''

    def __init__(self, _report):
        self.report = _report
        self.template_tree = self.generate_template_tree()
        self.source_file_map = self.generate_fragments_mapping()

    @staticmethod
    def setup_paths(metadata, doc_var):
        """
        Prepares the environment to generate the necessary files (e.g. output, temp, logs, hashes, figures, ...)
        :param metadata: Report metadata
        :param doc_var: Document variable
        :return: None
        """
        def _build_subpath(directory):
            return os.path.join(metadata['report_path'], 'gen', metadata['doc_suffix'], directory)

        metadata['doc_suffix'] = ReportCompiler.get_doc_var_suffix(doc_var)
        dirs = ['fig', 'hash', 'log', 'tmp', 'out']
        for d in dirs:
            metadata['{}_path'.format(d)] = _build_subpath(d)
            if not os.path.exists(metadata['{}_path'.format(d)]):
                os.makedirs(metadata['{}_path'.format(d)], os.O_RDWR)
        metadata['data_path'] = os.path.join(metadata['report_path'], 'data')
        metadata['templates_path'] = os.path.join(metadata['report_path'], 'templates')
        metadata['src_path'] = os.path.join(metadata['report_path'], 'src')
        metadata['logger'] = metadata['name'] + '_' + metadata['doc_suffix']

    def generate_template_tree(self):
        """
        Scans the template directory and creates a template dependency tree (i.e. templates, subtemplates, ...)
        :return: Template dependency tree
        """
        root_template = Node(self.report.main_template)
        stack = [root_template]
        while len(stack) > 0:
            current_node = stack.pop()
            with open(os.path.join(self.report.path, 'templates', current_node.name)) as f:
                content = f.read()
            fragments_found = self.included_templates(content)
            for f in fragments_found:
                stack.append(Node(f, parent=current_node))

        return Tree(root_template)

    def generate_fragments_mapping(self):
        """
        Generates (and validates) the mapping between each template and its corresponding source code file.
        :return: Template/source code file mapping
        """
        src_mapping = {}
        for fragment in PreOrderIter(self.template_tree.node):
            fragment_name = fragment.name
            fragment_basename, _ = os.path.splitext(fragment_name)
            fragment_code = glob(os.path.join(self.report.path, 'src', '{}.[a-zA-Z0-9]*'.format(fragment_basename)))
            if len(fragment_code) == 0:
                print('Warning: no source file for template "{}", context will be empty.'.format(fragment_basename))
            elif len(fragment_code) > 1:
                # No multiple files with different extensions, same name are allowed
                raise EnvironmentError('More than one source file for fragment {}'.format(fragment_basename))
            else:
                src_mapping[fragment_name] = fragment_code[0]  # Guaranteed to be only one
        return src_mapping

    @staticmethod
    def setup_logger(report_metadata, debug_level):
        """
        Initializes and sets up logger
        :param report_metadata: Report metadata
        :param debug_level: Debug level
        :return: Logger
        """
        logger = logging.getLogger(report_metadata['logger'])
        log_path = report_metadata['log_path']
        file_handler = logging.FileHandler(os.path.join(log_path,
                                                        report_metadata['doc_suffix'] +
                                                        '__' +
                                                        datetime.now().strftime('%Y_%m_%d__%H_%M_%S') +
                                                        '.log'))
        formatter = logging.Formatter(ReportCompiler.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        logger.setLevel(debug_level)
        logger.addHandler(file_handler)
        return logger

    def generate(self, doc_vars, report_metadata,  n_doc_workers=2, n_frag_workers=2, debug_level=logging.DEBUG):
        """
        Generates documents from a list of document variables.
        :param doc_vars: List of document variables, where each document variable is a dictionary with variables
        associated with a document.
        :param report_metadata: Report metadata
        :param n_doc_workers: Number of concurrent document-generating threads.
        :param n_frag_workers: Number of concurrent fragment-generating threads. The total number threads will be
        n_doc_workers * n_frag_workers.
        :param debug_level: Debug level
        :return: None
        """
        results = []
        with ThreadPoolExecutor(max_workers=n_doc_workers) as executor:
            for doc_var in doc_vars:
                report_metadata_copy = deepcopy(report_metadata)  # To avoid parallelism issues
                ReportCompiler.setup_paths(report_metadata_copy, doc_var)
                worker = self._generate_doc(doc_var, report_metadata_copy, n_frag_workers, debug_level=debug_level)
                result = executor.submit(worker)
                result.doc = report_metadata_copy['doc_suffix']
                results.append(result)
            executor.shutdown(wait=True)

        error_results = [r for r in results if r.exception() is not None]
        n_errors = len(error_results)
        if n_errors > 0:
            traceback_dict = {}
            for result in error_results:
                error = result.exception()
                if isinstance(error, FragmentGenerationError):
                    traceback_dict.update(error.fragment_errors)
                else:
                    error_msg = str(error) + '\n' + ''.join(traceback.format_tb(error.__traceback__))
                    traceback_dict.update({result.doc: {'<global>': error_msg}})
            raise FragmentGenerationError('Error on document(s) generation:\n', traceback_dict)

    def _generate_fragment(self, _fragment, _doc_var, _report_metadata):
        """
        Returns a function that generates a fragment for a particular document, used by the ThreadPoolExecutor
        :param _fragment: Fragment name
        :param _doc_var: Document variable
        :param _report_metadata: Report metadata
        :return: Function that generates a fragment
        """
        def func():
            fragment_name = _fragment.name
            fragment_path = _fragment.path
            fragment_path = '/'.join([elem.name for elem in fragment_path])
            # Deep copy to avoid concurrency issues in parallel computation
            doc_var_copy = deepcopy(_doc_var)
            report_metadata = deepcopy(_report_metadata)
            if self.source_file_map.get(fragment_name):
                current_frag_context = FragmentCompiler.compile(self.source_file_map[fragment_name], doc_var_copy,
                                                                report_metadata)
            else:
                current_frag_context = {}
            if not isinstance(current_frag_context, dict):
                current_frag_context = {'data': current_frag_context}
            return current_frag_context, fragment_path
        return func

    def _generate_doc(self, _doc_var, _report_metadata, n_frag_workers=2, debug_level=logging.DEBUG):
        """
        Returns a function that generates a document, used by the ThreadPoolExecutor
        :param _doc_var: Document variable
        :param _report_metadata: Report metadata
        :param n_frag_workers: Number of concurrent fragment-generating threads
        :param debug_level: Debug level
        :return: Function that generates a document
        """
        def func():
            doc_var = _doc_var
            report_metadata = _report_metadata

            logger = ReportCompiler.setup_logger(report_metadata, debug_level)
            logger.info('[{}] Generating document...'.format(report_metadata['doc_suffix']))
            # fragment_compiler = FragmentCompiler(self.report.name, self.report.path)
            sys.path.append(os.path.join(self.report.path, 'src'))

            results = []
            with ThreadPoolExecutor(max_workers=n_frag_workers) as executor:
                for fragment in PreOrderIter(self.template_tree.node):
                    report_metadata_copy = deepcopy(report_metadata)  # To avoid parallelism issues
                    worker = self._generate_fragment(fragment, doc_var, report_metadata_copy)
                    result = executor.submit(worker)
                    result.fragment = os.path.splitext(fragment.name)[0]
                    results.append(result)
                executor.shutdown(wait=True)

            errors = [r for r in results if r.exception() is not None]
            n_errors = len(errors)
            if n_errors > 0:
                frag_errors = {report_metadata['doc_suffix']: {}}
                for result in [r for r in results if r.exception() is not None]:
                    frag_errors[report_metadata['doc_suffix']][result.fragment] = (
                        result.exception().args[0],
                        traceback.format_tb(result.exception().__traceback__)
                    )
                exception = FragmentGenerationError('Error on fragment(s) generation ({})...'.format(n_errors),
                                                    frag_errors)
                logger.error(exception)
                raise exception

            fragments_context = {}
            for result in results:
                if result.exception() is None:
                    current_frag_context, fragment_path = result.result()
                    ReportCompiler.update_nested_dict(fragments_context, fragment_path, current_frag_context)

            context = {'data': fragments_context, 'meta': report_metadata}
            sys.path = sys.path[:-1]

            if report_metadata.get('generate_context_file') and report_metadata['generate_context_file']:
                logger.info('[{}] Generating context file...'.format(report_metadata['doc_suffix']))
                suffix = report_metadata['doc_suffix']
                file_name = 'document.json' if suffix == '' else suffix + '.json'
                with open(os.path.join(report_metadata['tmp_path'], file_name), 'w') as f:
                    f.write(json.dumps(context, indent=2, sort_keys=True))

            context['meta']['template_context_info'] = \
                [(node.name, '.'.join([os.path.splitext(path_node.name)[0] for path_node in node.path][1:]))
                 for node in PreOrderIter(self.template_tree.node)
                 ]
            output_doc = ReportCompiler.render_template(doc_var, context)
            ReportCompiler.postprocess(output_doc, doc_var, context)
            logger.info('[{}] Document generated'.format(report_metadata['doc_suffix']))
            return output_doc
        return func

    def included_templates(self, content):
        """
        Returns the number of child templates included in content, according to the report template renderer engine
        :param content: String content of the parent template
        :return: List of child templates included in content
        """
        try:
            renderer = TemplateRenderer.get(id=self.report.config['template_renderer'])
        except KeyError:
            renderer = TemplateRenderer.get()  # Default renderer

        return renderer.included_templates(content)

    @staticmethod
    def render_template(doc_var, context):
        """
        Performs the template rendering stage for the report (see architecture)
        :param doc_var: Document variable
        :param context: Full context with two keys: 'data' for context generation output and 'meta' for report metadata
        :return: Template rendering engine output, generally the rendered template
        """
        try:
            renderer = TemplateRenderer.get(
                id=context['meta']['template_renderer'])
        except KeyError:
            renderer = TemplateRenderer.get()  # Default renderer

        logger = logging.getLogger(context['meta']['logger'])
        logger.debug('[{}] Rendering template ({})...'.format(context['meta']['doc_suffix'],
                                                              renderer.__class__.__name__))
        return renderer.render_template(context['meta']['templates_path'],
                                        context['meta']['main_template'],
                                        doc_var,
                                        context)

    @staticmethod
    def postprocess(doc, doc_var, context):
        """
        Performs the postprocessing stages for the report (see architecture). Multiple stages can be defined.
        :param doc: Document content, output from the template rendering stage
        :param doc_var: Document variable
        :param context: Full context with two keys: 'data' for context generation output and 'meta' for report metadata
        :return: None
        """
        try:
            postprocessors_info = context['meta']['postprocessor']
            if not isinstance(postprocessors_info, list):
                postprocessors_info = [postprocessors_info]
        except KeyError:
            postprocessors_info = []

        for postprocessor_info in postprocessors_info:
            postprocessor = PostProcessor.get(id=postprocessor_info)
            logger = logging.getLogger(context['meta']['logger'])
            logger.debug('[{}] Postprocessing ({})...'.format(context['meta']['doc_suffix'],
                                                              postprocessor.__class__.__name__))
            postprocessor.postprocess(doc_var, doc, postprocessor_info, context)

    @staticmethod
    def update_nested_dict(doc_context, fragment, frag_context):
        """
        Updates a dictionary recursively, forming a nested structure according to the template tree structure
        :param doc_context: Context/dictionary to be updated
        :param fragment: Path of the new fragment from the template root, used as the new key path
        :param frag_context: Dictionary to be inserted in doc_context
        :return: Updated document context
        """
        head, tail = os.path.split(fragment)
        fragment_items = []
        while head != '':
            tail_name, _ = os.path.splitext(tail)
            fragment_items.append(tail_name)
            head, tail = os.path.split(head)
        fragment_items.reverse()

        aux_dict = doc_context
        for item in fragment_items:
            if aux_dict.get(item) is None:
                aux_dict[item] = {}
            aux_dict = aux_dict[item]
        aux_dict.update(frag_context)


class FragmentCompiler:
    """ Class responsible for compiling a fragment within a document """
    @staticmethod
    def compile(fragment, doc_var, report_metadata):
        """
        Compiles a fragment within a document with the given document variables
        :param fragment: Fragment path from template root
        :param doc_var: Document variable
        :param report_metadata: Report metadata
        :return: Dictionary with the context of the specified fragment, to be used in the template rendering stage
        """
        metadata = report_metadata
        metadata['fragment_path'] = fragment
        metadata['fragment_name'] = os.path.splitext(os.path.basename(fragment))[0]

        fragment_metadata = FragmentCompiler.retrieve_fragment_metadata(doc_var, metadata)
        metadata.update(fragment_metadata)
        doc_var_augmented = FragmentCompiler.prefetch_data(doc_var, metadata)
        fragment_data = FragmentCompiler.fetch_data(doc_var_augmented, metadata)
        return FragmentCompiler.generate_context(fragment_data, doc_var_augmented, metadata)

    @staticmethod
    def retrieve_fragment_metadata(doc_var, metadata):
        """
        Stage to extract metadata from within the fragment's source code (see architecture)
        :param doc_var: Document variable
        :param metadata: Report metadata
        :return: Fragment metadata dictionary
        """
        _, file_extension = os.path.splitext(metadata['fragment_path'])
        try:
            retriever_name = metadata['metadata_retriever'][file_extension]
            retriever = FragmentMetadataRetriever.get(id=retriever_name)
        except KeyError:
            retriever = FragmentMetadataRetriever.get(extension=file_extension)
        logger = logging.getLogger(metadata['logger'])
        logger.debug('[{}] {}: Retrieving metadata ({})...'.format(metadata['doc_suffix'],
                                                                   metadata['fragment_name'],
                                                                   retriever.__class__.__name__))
        return retriever.retrieve_fragment_metadata(doc_var, metadata)

    @staticmethod
    def prefetch_data(doc_var, metadata):
        """
        Stage to "augment" the document variable with necessary data for future stages (see architecture)
        :param doc_var: Document variable
        :param metadata: Metadata (report metadata, overriden by fragment)
        :return: Document variable "augmented" with the specified additional data
        """
        try:
            prefetchers_info = metadata['predata_fetcher']
        except KeyError:
            prefetchers_info = []  # No prefetchers specified

        if not isinstance(prefetchers_info, list):
            prefetchers_info = [prefetchers_info]

        predata = []
        for i, prefetcher_info in enumerate(prefetchers_info):
            prefetcher = FragmentDataFetcher.get(id=prefetcher_info)
            logger = logging.getLogger(metadata['logger'])
            prefetcher_name = prefetcher_info.get('name') if prefetcher_info.get('name') else '#' + str(i)
            logger.debug("[{}] {}: Prefetching data ('{}': {})...".format(metadata['doc_suffix'],
                                                                          metadata['fragment_name'],
                                                                          prefetcher_name,
                                                                          prefetcher.__class__.__name__))
            predata.append(prefetcher.fetch(doc_var, prefetcher_info, metadata))

        for datum in predata:
            if len(datum.index) > 1:
                message = '{}: Pre-Data fetcher returning more than one row'.format(metadata['fragment_path'])
                logger = logging.getLogger(metadata['logger'])
                logger.error('[{}] {}'.format(metadata['doc_suffix'], message))
                raise ValueError(message)

        flattened_predata = dict(ChainMap(*[df.ix[0, :].to_dict() for df in predata]))
        flattened_predata.update(doc_var)

        return flattened_predata

    @staticmethod
    def fetch_data(doc_var, metadata):
        """
        Stage to fetch the data to be used in the context generation stage (see architecture)
        :param doc_var: Document variable (augmented by prefetching)
        :param metadata: Metadata (report metadata, overriden by fragment)
        :return: Pandas dataframe (or list of dataframes) with required data
        """
        try:
            fetchers_info = metadata['data_fetcher']
        except KeyError:
            message = '{}: Data fetcher not specified'.format(metadata['fragment_path'])
            logger = logging.getLogger(metadata['logger'])
            logger.error('[{}] {}'.format(metadata['doc_suffix'], message))
            raise NotImplementedError(message)

        if not isinstance(fetchers_info, list):
            fetchers_info = [fetchers_info]

        data = OrderedDict()
        for i, fetcher_info in enumerate(fetchers_info):
            fetcher = FragmentDataFetcher.get(id=fetcher_info)
            logger = logging.getLogger(metadata['logger'])
            fetcher_name = fetcher_info.get('name') if fetcher_info.get('name') else '#' + str(i)
            logger.debug("[{}] {}: Fetching data ('{}': {})...".format(metadata['doc_suffix'],
                                                                       metadata['fragment_name'],
                                                                       fetcher_name,
                                                                       fetcher.__class__.__name__))
            dt = fetcher.fetch(doc_var, fetcher_info, metadata)
            if not isinstance(fetcher_info, dict) or fetcher_info.get('name') is None:
                fetcher_id = str(i)
            else:
                fetcher_id = fetcher_info['name']
            if data.get('fetcher_id') is not None:
                message = 'Data fetcher id is duplicated {}'.format(fetcher_id)
                logger.error('[{}] {}'.format(metadata['doc_suffix'], message))
                raise NotImplementedError(message)
            data[fetcher_id] = dt

        if len(data) == 0:
            data = pd.DataFrame()

        return data

    @staticmethod
    def generate_context(fragment_data, doc_var, metadata):
        """
        Stage to generate dictionary to be used as context for template rendering stage
        :param fragment_data: Pandas dataframe (or list of dataframes) with the current fragment's data
        :param doc_var: Document variable (augmented by prefetching)
        :param metadata: Metadata (report metadata, overriden by fragment)
        :return: Dictionary with the context of the current fragment, to be used in the template rendering stage
        """
        logger = logging.getLogger(metadata['logger'])
        _, file_extension = os.path.splitext(metadata['fragment_path'])

        generator = None
        try:
            generator_info = metadata['context_generator']
            if isinstance(generator_info, str):
                generator = FragmentContextGenerator.get(id=generator_info)
            elif isinstance(generator_info, dict):
                generator = FragmentContextGenerator.get(id=generator_info[file_extension])
            else:
                pass  # Context generator invalid, ignoring...

        except KeyError:
            pass

        if generator is None:
            try:
                generator = FragmentContextGenerator.get(extension=file_extension)
            except KeyError:
                message = 'Data fetcher not specified for fragment {}'.format(metadata['fragment_name'])
                logger.error('[{}] {}'.format(metadata['doc_suffix'], message))
                raise NotImplementedError(message)

        context = generator.generate_context_wrapper(doc_var, fragment_data, metadata)
        return context


if __name__ == '__main__':
    try:
        report = Report('C:\\Users\\47873315B\\Dropbox\\ICO\\ReportCompiler\\reports\\FactSheetTest')
        # report = Report('C:\\Users\\47873315B\\Dropbox\\ICO\\ReportCompiler\\reports\\TestRMarkdown')
        # report = Report(repo_url='http://icosrvprec02/gitlab/informationcenter/report_factsheet-test.git',
        #                 repo_path='I:/d_gomez/reports')
        report.generate([{'iso': iso} for iso in ['ESP', ]], n_doc_workers=3, n_frag_workers=2)
        print('All documents generated successfully!')
    except FragmentGenerationError as e:
        print(e)
