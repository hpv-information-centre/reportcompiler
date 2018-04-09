""" reportcompilers.py

This module is responsible for the compilation of the reports (ReportCompiler)
and its fragments (FragmentCompiler).

"""

import os
import traceback
import logging
import json
import sys
from collections import OrderedDict, ChainMap, namedtuple
from glob import glob
from copy import deepcopy
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from anytree import PreOrderIter, Node, RenderTree as Tree
from reportcompiler.plugins.data_fetchers.base import DataFetcher
from reportcompiler.plugins.source_parsers.base \
    import SourceParser
from reportcompiler.plugins.template_renderers.base import TemplateRenderer
from reportcompiler.plugins.postprocessors.base import PostProcessor
from reportcompiler.errors import FragmentGenerationError

__all__ = ['ReportCompiler', 'FragmentCompiler', ]


class ReportCompiler:
    """ Class responsible for compiling a report into a document """
    LOG_FORMAT = '%(asctime)-15s %(message)s'

    @staticmethod
    def get_doc_var_suffix(doc_var):
        """
        Generates a unique suffix given a particular document variable.
        :param OrderedDict doc_var: Document variable
        :returns: String with a representation of the document variable, to be
        used as a filename suffix
        :rtype: str
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
            suffix = suffix.replace(': ', '=')
            return suffix
        except KeyError:
            return ''

    def __init__(self, _report):
        self.report = _report
        try:
            self.renderer = TemplateRenderer.get(
                id=self.report.metadata['template_renderer'])
        except KeyError:
            self.renderer = TemplateRenderer.get()  # Default renderer

        self.template_tree = self.generate_template_tree()
        self.source_file_map = self.generate_fragments_mapping()

    @staticmethod
    def fetch_info(doc_var, metadata):
        """
        Fetches the information about the allowed document variables.
        :param OrderedDict doc_var: Document variable
        :param dict metadata: Report metadata
        :returns: Dictionary with the allowed values for mandatory variables.
        :rtype: dict
        """
        return FragmentCompiler.fetch_info(
                                doc_var=doc_var,
                                fetcher_key='param_config',
                                metadata=metadata)

    @staticmethod
    def setup_environment(metadata, doc_var):
        """
        Prepares the environment to generate the necessary files (e.g. output,
        temp, logs, hashes, figures, ...) and variables.
        :param dict metadata: Report metadata
        :param OrderedDict doc_var: Document variable
        """
        def _build_subpath(directory):
            return os.path.join(metadata['report_path'],
                                'gen',
                                metadata['doc_suffix'],
                                directory)

        metadata['doc_suffix'] = ReportCompiler.get_doc_var_suffix(doc_var)
        dirs = ['fig',  # Generated figures
                'hash',  # Hashes used as cache checks to reuse generated data:
                         # * .hash files contain the hashes of code, data,
                         #   metadata and doc_var
                         # * .ctx files contain the generated contexts to be
                         #   reused if the hashes match
                'log',  # Logs detailing the document generation
                'tmp',  # Temporary directory
                'out',  # Output directory
                ]
        for d in dirs:
            metadata['{}_path'.format(d)] = _build_subpath(d)
            if not os.path.exists(metadata['{}_path'.format(d)]):
                os.makedirs(metadata['{}_path'.format(d)], os.O_RDWR)
        metadata['data_path'] = os.path.join(metadata['report_path'], 'data')
        metadata['templates_path'] = os.path.join(metadata['report_path'],
                                                  'templates')
        metadata['src_path'] = os.path.join(metadata['report_path'], 'src')
        metadata['logger_name'] = 'reportcompiler.' + (metadata['name'] +
                                                       '_' +
                                                       metadata['doc_suffix'])

    def generate_template_tree(self):
        """
        Scans the template directory and creates a template dependency tree
        (i.e. templates, subtemplates, ...).
        :returns: Template dependency tree
        :rtype: anytree.Tree
        """
        root_template = Node(self.report.main_template)
        stack = [root_template]
        while len(stack) > 0:
            current_node = stack.pop()
            with open(os.path.join(self.report.path,
                                   'templates',
                                   current_node.name)) as f:
                content = f.read()
            fragments_found = self.included_templates(content)
            for f in fragments_found:
                stack.append(Node(f, parent=current_node))

        return Tree(root_template)

    def generate_fragments_mapping(self):
        """
        Generates (and validates) the mapping between each template and its
        corresponding source code file.
        :returns: Template/source code file mapping
        :rtype: dict
        """
        src_mapping = {}
        for fragment in PreOrderIter(self.template_tree.node):
            fragment_name = fragment.name
            fragment_basename, _ = os.path.splitext(fragment_name)
            fragment_code = glob(os.path.join(self.report.path,
                                              'src',
                                              '{}.[a-zA-Z0-9]*'.format(
                                                  fragment_basename)))
            if len(fragment_code) == 0:
                print('Warning: no source file '
                      'for template "{}", context will be empty.'.format(
                          fragment_basename))
            elif len(fragment_code) > 1:
                # Files with different extensions, same name are not allowed
                raise EnvironmentError(
                    'More than one source file for fragment {}'.
                    format(fragment_basename))
            else:
                # Guaranteed to be only one
                src_mapping[fragment_name] = fragment_code[0]
        return src_mapping

    @staticmethod
    def setup_logger(report_metadata, log_level):
        """
        Initializes and sets up the logger.
        :param dict report_metadata: Report metadata
        :param int log_level: Log level
        """
        logger = logging.getLogger(report_metadata['logger_name'])
        log_path = report_metadata['log_path']
        file_handler = logging.FileHandler(
            os.path.join(log_path,
                         report_metadata['doc_suffix'] +
                         '__' +
                         datetime.now().strftime(
                             '%Y_%m_%d__%H_%M_%S') +
                         '.log'))
        formatter = logging.Formatter(ReportCompiler.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        logger.setLevel(log_level)
        logger.addHandler(file_handler)

    @staticmethod
    def shutdown_loggers():
        """
        Shutdowns the logger and its handlers.
        :param dict report_metadata: Report metadata
        """
        loggers = (logger for logger_name, logger
                   in logging.getLogger().manager.loggerDict.items()
                   if logger_name.startswith('reportcompiler.'))

        for logger in loggers:
            handlers = logger.handlers[:]
            for handler in handlers:
                handler.close()
                logger.removeHandler(handler)

        # for handler in logger.handlers:
        #     logger.removeHandler(handler)

    def generate(self,
                 doc_vars,
                 report_metadata,
                 n_doc_workers=2,
                 n_frag_workers=2,
                 debug_mode=False,
                 log_level=logging.DEBUG):
        """
        Generates documents from a list of document variables.
        :param dict doc_vars: List of document variables, where each document
            variable is a dictionary with variables associated with a document.
        :param dict report_metadata: Report metadata
        :param int n_doc_workers: Number of concurrent document-generating
            threads.
        :param int n_frag_workers: Number of concurrent fragment-generating
            threads. The total thread count will be
            n_doc_workers * n_frag_workers.
        :param boolean debug_mode: If enabled, the document generation will
            be limited to one thread and several measures will be taken to
            facilitate debugging: each
        :param int log_level: Log level
        """
        if debug_mode:
            n_doc_workers = 1
            n_frag_workers = 1
            self._pre_doc_generation(report_metadata)

        report_metadata['debug_mode'] = debug_mode

        doc_info = namedtuple('doc_info', ['doc', 'result', 'exception'])
        results = []
        if n_doc_workers == 1:
            # If there is only one worker, do it in the same process
            # (easier to debug)
            for doc_var in doc_vars:
                result = None
                ReportCompiler.setup_environment(report_metadata,
                                                 doc_var)
                ReportCompiler.setup_logger(report_metadata,
                                            log_level)
                try:
                    result = self._generate_doc(doc_var,
                                                report_metadata,
                                                n_frag_workers)
                    exception = None
                except Exception as e:
                    exception = e
                doc_info = doc_info(doc=doc_var,
                                    result=result,
                                    exception=exception)
                results.append(doc_info)
        else:
            future_results = []
            with ProcessPoolExecutor(max_workers=n_doc_workers) as executor:
                for doc_var in doc_vars:
                    # To avoid parallelism issues
                    report_metadata_copy = deepcopy(report_metadata)
                    ReportCompiler.setup_environment(report_metadata_copy, 
                                                     doc_var)
                    ReportCompiler.setup_logger(report_metadata_copy,
                                                log_level)
                    worker = self._generate_doc
                    result = executor.submit(worker,
                                             doc_var,
                                             report_metadata_copy,
                                             n_frag_workers)
                    result.doc = report_metadata_copy['doc_suffix']
                    future_results.append(result)
                executor.shutdown(wait=True)
            for result in future_results:
                info = doc_info(doc=result.doc,
                                result=result.result(),
                                exception=result.exception())

        ReportCompiler.shutdown_loggers()

        if debug_mode:
            self._post_doc_generation(report_metadata)

        error_results = [r for r in results if r.exception is not None]
        n_errors = len(error_results)
        if n_errors > 0:
            traceback_dict = {}
            for result in error_results:
                error = result.exception
                if isinstance(error, FragmentGenerationError):
                    traceback_dict.update(error.fragment_errors)
                else:
                    error_msg = (str(error) + '\n' +
                                 ''.join(
                                        traceback.format_tb(
                                            error.__traceback__)))
                    traceback_dict.update({result.doc: {
                                            '<global>': error_msg}})
            raise FragmentGenerationError(
                'Error on document(s) generation:\n', traceback_dict)

    def _pre_doc_generation(self, report_metadata):
        """
        Actions made before starting the document generation process.
        :param dict report_metadata: Report metadata
        """
        meta_dir = os.path.join(report_metadata['report_path'], '..', '_meta')
        for f in glob(os.path.join(meta_dir, 'error_*')):
            os.remove(f)
        if os.path.exists(os.path.join(meta_dir, 'last_debug_errors')):
            os.remove(os.path.join(meta_dir, 'last_debug_errors'))

    def _post_doc_generation(self, report_metadata):
        """
        Actions made after finishing the document generation process.
        :param dict report_metadata: Report metadata
        """
        meta_dir = os.path.join(report_metadata['report_path'], '..', '_meta')
        last_errors_file = open(os.path.join(meta_dir,
                                             'last_debug_errors'), 'w')
        last_errors_file.write('[\n')
        for i, f in enumerate(glob(os.path.join(meta_dir, 'error_*'))):
            with open(f, 'r') as error_file:
                if i > 0:
                    last_errors_file.write(',\n')
                last_errors_file.write(error_file.read())
            os.remove(f)
        last_errors_file.write('\n]')
        last_errors_file.close()

    def _generate_fragment(self, fragment, doc_var, report_metadata):
        """
        Returns a function that generates a fragment for a particular document,
        used by the ProcessPoolExecutor.
        :param str fragment: Fragment name
        :param OrderedDict doc_var: Document variable
        :param dict report_metadata: Report metadata
        :returns: Function that generates a fragment
        :rtype: function
        """
        _fragment_name = fragment.name
        _fragment_path = fragment.path
        _fragment_path = '/'.join([elem.name for elem in _fragment_path])
        # Deep copy to avoid concurrency issues in parallel computation
        # TODO: Try to avoid copies
        _doc_var = deepcopy(doc_var)
        _report_metadata = deepcopy(report_metadata)
        if self.source_file_map.get(_fragment_name):
            current_frag_context = FragmentCompiler.compile(
                self.source_file_map[_fragment_name],
                _doc_var,
                _report_metadata)
        else:
            current_frag_context = {}
        if not isinstance(current_frag_context, dict):
            current_frag_context = {'data': current_frag_context}
        return current_frag_context, _fragment_path

    def _generate_doc(self,
                      doc_var,
                      report_metadata,
                      n_frag_workers=2):
        """
        Returns a function that generates a document, used by the
        ProcessPoolExecutor.
        :param OrderedDict _doc_var: Document variable
        :param dict _report_metadata: Report metadata
        :param int n_frag_workers: Number of concurrent fragment-generating
            threads
        :returns: Function that generates a document
        :rtype: function
        """
        augmented_doc_var = ReportCompiler.augment_doc_var(doc_var,
                                                           report_metadata)
        logger = logging.getLogger(report_metadata['logger_name'])
        logger.info('[{}] Generating document...'.format(
            report_metadata['doc_suffix']))
        sys.path.append(os.path.join(self.report.path, 'src'))

        fragment_info = namedtuple('fragment_info', ['fragment',
                                                     'result',
                                                     'exception'])
        results = []
        if n_frag_workers == 1:
            # If there is only one worker, do it in the same process
            # (easier to debug)
            for fragment in PreOrderIter(self.template_tree.node):
                result = None
                try:
                    result = self._generate_fragment(fragment,
                                                     augmented_doc_var,
                                                     report_metadata)
                    exception = None
                except Exception as e:
                    exception = e
                frag_info = fragment_info(fragment=fragment,
                                          result=result,
                                          exception=exception)
                results.append(frag_info)
        else:
            future_results = []
            with ProcessPoolExecutor(max_workers=n_frag_workers) as executor:
                for fragment in PreOrderIter(self.template_tree.node):
                    # To avoid parallelism issues
                    _report_metadata = deepcopy(report_metadata)
                    worker = self._generate_fragment
                    result = executor.submit(worker,
                                             fragment,
                                             augmented_doc_var,
                                             _report_metadata)
                    result.fragment = os.path.splitext(fragment.name)[0]
                    future_results.append(result)
                executor.shutdown(wait=True)

                for r in future_results:
                    frag_info = fragment_info(fragment=r.fragment,
                                              result=r.result(),
                                              exception=r.exception())
                    results.append(frag_info)

        errors = [r for r in results if r.exception is not None]
        n_errors = len(errors)
        if n_errors > 0:
            frag_errors = {report_metadata['doc_suffix']: {}}
            for result in [r
                           for r in results
                           if r.exception is not None]:
                frag_errors[
                        report_metadata['doc_suffix']][result.fragment] = (
                    result.exception.args[0],
                    traceback.format_tb(result.exception.__traceback__)
                )
            exception = FragmentGenerationError(
                'Error on fragment(s) generation ({})...'.
                format(n_errors),
                frag_errors)
            logger.error(exception)
            raise exception

        fragments_context = {}
        for result in results:
            if result.exception is None:
                current_frag_context, fragment_path = result.result
                ReportCompiler.update_nested_dict(fragments_context,
                                                  fragment_path,
                                                  current_frag_context)

        context = {'data': fragments_context, 'meta': report_metadata}
        sys.path = sys.path[:-1]

        context['meta']['template_context_info'] = \
            [(
                node.name, '.'.join(
                    [os.path.splitext(path_node.name)[0]
                        for path_node in node.path][1:]))
                for node in PreOrderIter(self.template_tree.node)
             ]
        output_doc = ReportCompiler.render_template(augmented_doc_var,
                                                    context)
        ReportCompiler.postprocess(output_doc, augmented_doc_var, context)
        logger.info('[{}] Document generated'.format(
            report_metadata['doc_suffix']))
        return output_doc

    def included_templates(self, content):
        """
        Returns the number of child templates included in content, according
        to the report template renderer engine.
        :param str content: String content of the parent template
        :returns: List of child templates included in content
        :rtype: list
        """

        return self.renderer.included_templates(content)

    @staticmethod
    def render_template(doc_var, context):
        """
        Performs the template rendering stage for the report
        (see architecture).
        :param OrderedDict doc_var: Document variable
        :param dict context: Full context with two keys: 'data' for context
        generation output and 'meta' for report metadata
        :returns: Template rendering engine output, generally the rendered
        template
        :rtype: object
        """
        try:
            renderer = TemplateRenderer.get(
                id=context['meta']['template_renderer'])
        except KeyError:
            renderer = TemplateRenderer.get()  # Default renderer

        logger = logging.getLogger(context['meta']['logger_name'])
        logger.debug('[{}] Rendering template ({})...'.format(
            context['meta']['doc_suffix'],
            renderer.__class__.__name__))
        return renderer.render_template(doc_var, context)

    @staticmethod
    def postprocess(doc, doc_var, context):
        """
        Performs the postprocessing stages for the report (see architecture).
        Multiple stages can be defined.
        :param object doc: Document content, output from the template
            rendering stage
        :param OrderedDict doc_var: Document variable
        :param dict context: Full context with two keys: 'data' for context
        generation output and 'meta' for report metadata
        """
        try:
            postprocessors_info = context['meta']['postprocessor']
            if not isinstance(postprocessors_info, list):
                postprocessors_info = [postprocessors_info]
        except KeyError:
            postprocessors_info = []

        for postprocessor_info in postprocessors_info:
            postprocessor = PostProcessor.get(id=postprocessor_info)
            logger = logging.getLogger(context['meta']['logger_name'])
            logger.debug('[{}] Postprocessing ({})...'.format(
                context['meta']['doc_suffix'],
                postprocessor.__class__.__name__))
            postprocessor.postprocess(doc_var,
                                      doc,
                                      postprocessor_info,
                                      context)

    @staticmethod
    def update_nested_dict(doc_context, fragment, frag_context):
        """
        Updates a dictionary recursively, forming a nested structure according
        to the template tree structure.
        :param dict doc_context: Context/dictionary to be updated
        :param str fragment: Path of the new fragment from the template root,
            used as the new key path
        :param dict frag_context: Dictionary to be inserted in doc_context
        :returns: Updated document context
        :rtype: dict
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

    @staticmethod
    def augment_doc_var(doc_var, metadata):
        """
        Stage to "augment" the document variable with necessary additional data
            for the document generation.
        :param OrderedDict doc_var: Document variable
        :param dict metadata: Metadata
        :returns: Document variable "augmented" with the specified additional
            data
        :rtype: dict
        """
        logger = logging.getLogger(metadata['logger_name'])
        message = 'Starting doc_var augmentation...'
        logger.info('[{}] {}'.format(metadata['doc_suffix'], message))
        predata = FragmentCompiler.fetch_info(doc_var,
                                              'param_augmentation',
                                              metadata)
        if len(predata) > 0:
            flattened_predata = dict(ChainMap(*[df.ix[0, :].to_dict()
                                                for df in predata.values()]))
        else:
            flattened_predata = {}
        doc_var_augmented = deepcopy(doc_var)
        doc_var_augmented.update(flattened_predata)
        return doc_var_augmented


class FragmentCompiler:
    """ Class responsible for compiling a fragment within a document """
    @staticmethod
    def compile(fragment, doc_var, report_metadata):
        """
        Compiles a fragment within a document with the given document
            variables.
        :param str fragment: Fragment path from template root
        :param OrderedDict doc_var: Document variable
        :param dict report_metadata: Report metadata
        :returns: Context of the specified fragment, to be
            used in the template rendering stage
        :rtype: dict
        """
        metadata = report_metadata
        metadata['fragment_path'] = fragment
        metadata['fragment_name'] = os.path.splitext(
            os.path.basename(fragment))[0]

        fragment_metadata = FragmentCompiler.retrieve_fragment_metadata(
            doc_var,
            metadata)
        metadata.update(fragment_metadata)
        fragment_data = FragmentCompiler.fetch_data(doc_var,
                                                    metadata)
        return FragmentCompiler.generate_context(fragment_data,
                                                 doc_var,
                                                 metadata)

    @staticmethod
    def retrieve_fragment_metadata(doc_var, metadata):
        """
        Stage to extract metadata from within the fragment's source code (see
        architecture).
        :param OrderedDict doc_var: Document variable
        :param dict metadata: Report metadata
        :returns: Fragment metadata dictionary
        :rtype: dict
        """
        _, file_extension = os.path.splitext(metadata['fragment_path'])
        try:
            retriever_name = metadata['metadata_retriever'][file_extension]
            retriever = SourceParser.get(id=retriever_name)
        except KeyError:
            retriever = SourceParser.get(extension=file_extension)
        logger = logging.getLogger(metadata['logger_name'])
        logger.debug(
            '[{}] {}: Retrieving metadata ({})...'.
            format(metadata['doc_suffix'],
                   metadata['fragment_name'],
                   retriever.__class__.__name__))
        return retriever.retrieve_fragment_metadata(doc_var, metadata)

    @staticmethod
    def fetch_data(doc_var, metadata):
        """
        Stage to fetch the data to be used in the context generation stage

        (see architecture).
        :param OrderedDict doc_var: Document variable
        :param dict metadata: Metadata (report metadata, overriden by fragment)
        :returns: Pandas dataframe (or list of dataframes) with required data
        :rtype: pandas.DataFrame
        """
        logger = logging.getLogger(metadata['logger_name'])
        message = 'Starting data fetching...'
        logger.info('[{}] {}'.format(metadata['doc_suffix'], message))
        return FragmentCompiler.fetch_info(doc_var, 'data_fetcher', metadata)

    @staticmethod
    def fetch_info(doc_var, fetcher_key, metadata):
        """
        Fetches data according to fetcher_key.
        :param OrderedDict doc_var: Document variable
        :param dict metadata: Metadata (report metadata, overriden by fragment)
        :returns: Pandas dataframe (or list of dataframes) with required data
        :rtype: pandas.DataFrame
        """
        fragment_name = metadata.get('fragment_name')
        if fragment_name is None:
            # If it's None, we are fetching data for the report itself
            # (e.g. allowed doc_vars)
            fragment_name = fetcher_key

        doc_suffix = metadata.get('doc_suffix')
        if doc_suffix is None:
            doc_suffix = '-'

        logger_name = metadata.get('logger_name')
        if logger_name:
            logger = logging.getLogger(logger_name)
        else:
            logger = None

        try:
            fetchers_info = metadata[fetcher_key]
        except KeyError:
            message = '{}: Fetcher not specified'.format(
                fragment_name)
            if fetcher_key == 'fetch_data':
                # Fetcher mandatory for data fetchers
                if logger:
                    logger.error('[{}] {}'.format(metadata['doc_suffix'],
                                                  message))
                raise NotImplementedError(message)
            else:
                # Fetchers optional for other cases
                if logger:
                    logger.warning('[{}] {}'.format(metadata['doc_suffix'],
                                                    message))
                fetchers_info = []

        if not isinstance(fetchers_info, list):
            fetchers_info = [fetchers_info]

        data = OrderedDict()
        for i, fetcher_info in enumerate(fetchers_info):
            fetcher = DataFetcher.get(id=fetcher_info)
            if logger and metadata.get('fragment_name'):
                fetcher_name = fetcher_info.get('name')
                if fetcher_name is None:
                    fetcher_name = '#' + str(i)
                logger.debug(
                    "[{}] {}: Fetching data ('{}': {})...".format(
                        metadata['doc_suffix'],
                        metadata['fragment_name'],
                        fetcher_name,
                        fetcher.__class__.__name__))
            dt = fetcher.fetch(doc_var, fetcher_info, metadata)
            if (not isinstance(fetcher_info, dict) or
                    fetcher_info.get('name') is None):
                fetcher_id = str(i)
            else:
                fetcher_id = fetcher_info['name']
            if data.get('fetcher_id') is not None:
                message = 'Fetcher id is duplicated {}'.format(fetcher_id)
                if logger:
                    logger.error('[{}] {}'.format(
                        metadata['doc_suffix'],
                        message))
                raise NotImplementedError(message)
            data[fetcher_id] = dt

        return data

    @staticmethod
    def generate_context(fragment_data, doc_var, metadata):
        """
        Stage to generate dictionary to be used as context for template
        rendering stage.
        :param pandas.DataFrame fragment_data: Pandas dataframe (or list
            of dataframes) with the current fragment's data
        :param OrderedDict doc_var: Document variable
        :param dict metadata: Metadata (report metadata, overriden by fragment)
        :returns: Dictionary with the context of the current fragment, to be
            used in the template rendering stage
        :rtype: dict
        """
        logger = logging.getLogger(metadata['logger_name'])
        _, file_extension = os.path.splitext(metadata['fragment_path'])

        generator = None
        try:
            generator_info = metadata['context_generator']
            if isinstance(generator_info, str):
                generator = SourceParser.get(id=generator_info)
            elif isinstance(generator_info, dict):
                generator = SourceParser.get(
                    id=generator_info[file_extension])
            else:
                pass  # Context generator invalid, ignoring...

        except KeyError:
            pass

        if generator is None:
            try:
                generator = SourceParser.get(
                    extension=file_extension)
            except KeyError:
                message = 'Data fetcher not specified for fragment {}'.format(
                    metadata['fragment_name'])
                logger.error('[{}] {}'.format(metadata['doc_suffix'], message))
                raise NotImplementedError(message)

        context = generator.setup_and_generate_context(doc_var,
                                                       fragment_data,
                                                       metadata)
        return context
