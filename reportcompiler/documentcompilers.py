""" documentcompilers.py

This module is responsible for the compilation of the document specifications
(DocumentCompiler) and its fragments (FragmentCompiler).

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
from reportcompiler.plugins.template_renderers.base \
    import TemplateRenderer, TemplateRendererException
from reportcompiler.plugins.postprocessors.base \
    import PostProcessor, PostProcessorError
from reportcompiler.errors import DocumentGenerationError

__all__ = ['DocumentCompiler', 'FragmentCompiler', ]


class DocumentCompiler:
    """
    Class responsible for compiling a document specification into an
    actual document
    """
    LOG_FORMAT = '%(asctime)-15s %(message)s'

    @staticmethod
    def get_doc_param_suffix(doc_param):
        """
        Generates a unique suffix given a particular document variable.

        :param OrderedDict doc_param: Document variable
        :returns: String with a representation of the document variable, to be
            used as a filename suffix
        :rtype: str
        """
        try:
            if isinstance(doc_param, list) or isinstance(doc_param, tuple):
                suffix = '-'.join([str(v) for v in doc_param])
            elif isinstance(doc_param, dict):
                suffix = '-'.join([str(v) for v in list(doc_param.values())])
            elif isinstance(doc_param, str):
                suffix = doc_param
            else:
                raise ValueError('doc_param has invalid type')
            suffix = suffix.replace(': ', '=')
            return suffix
        except KeyError:
            return ''

    def __init__(self, _doc_spec):
        self.doc_spec = _doc_spec
        try:
            self.renderer = TemplateRenderer.get(
                id=self.doc_spec.metadata['template_renderer'])
        except KeyError:
            self.renderer = TemplateRenderer.get()  # Default renderer

        self.template_tree = self.generate_template_tree()
        self.source_file_map = self.generate_fragments_mapping()

    @staticmethod
    def fetch_allowed_param_values(doc_param, metadata):
        """
        Fetches the information about the allowed document variables.

        :param OrderedDict doc_param: Document variable
        :param dict metadata: Document metadata
        :returns: Dictionary with the allowed values for mandatory variables.
        :rtype: dict
        """
        return FragmentCompiler.fetch_info(
                                doc_param=doc_param,
                                fetcher_key='params_allowed_values',
                                metadata=metadata)

    @staticmethod
    def setup_environment(metadata, doc_param):
        """
        Prepares the environment to generate the necessary files (e.g. output,
        temp, logs, hashes, figures, ...) and variables.

        :param dict metadata: Document metadata
        :param OrderedDict doc_param: Document variable
        """
        def _build_subpath(directory):
            return os.path.join(metadata['docspec_path'],
                                'gen',
                                metadata['doc_suffix'],
                                directory)

        metadata['doc_suffix'] = \
            DocumentCompiler.get_doc_param_suffix(doc_param)
        dirs = ['fig',  # Generated figures
                'hash',  # Hashes used as cache checks to reuse generated data:
                         # * .hash files contain the hashes of code, data,
                         #   metadata and doc_param
                         # * .ctx files contain the generated contexts to be
                         #   reused if the hashes match
                'log',  # Logs detailing the document generation
                'tmp',  # Temporary directory
                'out',  # Output directory
                ]
        for d in dirs:
            metadata['{}_path'.format(d)] = _build_subpath(d)
            if not os.path.exists(metadata['{}_path'.format(d)]):
                os.makedirs(metadata['{}_path'.format(d)], 0o777)
        metadata['data_path'] = os.path.join(metadata['docspec_path'], 'data')
        metadata['templates_path'] = os.path.join(metadata['docspec_path'],
                                                  'templates')
        metadata['src_path'] = os.path.join(metadata['docspec_path'], 'src')
        metadata['logger_name'] = ('reportcompiler.' +
                                   metadata['doc_name'] +
                                   '_' +
                                   metadata['doc_suffix'])

    @staticmethod
    def _get_log_file_path(doc_metadata):
        return os.path.join(doc_metadata['log_path'],
                            datetime.now().strftime(
                               '%Y_%m_%d__%H_%M_%S') +
                            '__' +
                            doc_metadata['doc_suffix'] +
                            '.log')

    def generate_template_tree(self):
        """
        Scans the template directory and creates a template dependency tree
        (i.e. templates, subtemplates, ...).

        :returns: Template dependency tree
        :rtype: anytree.Tree
        """
        root_template = Node(self.doc_spec.main_template)
        stack = [root_template]
        while len(stack) > 0:
            current_node = stack.pop()
            try:
                with open(os.path.join(self.doc_spec.path,
                                       'templates',
                                       current_node.name)) as f:
                    content = f.read()
                fragments_found = self.included_templates(content)
                for f in fragments_found:
                    stack.append(Node(f, parent=current_node))
            except FileNotFoundError:
                common_template_dir = os.environ['RC_TEMPLATE_LIBRARY_PATH']
                if not os.path.exists(common_template_dir + current_node.name):
                    raise FileNotFoundError(
                        'Template {} does not exist in the document '
                        'specification nor in the '
                        'RC_TEMPLATE_LIBRARY_PATH ({})'.format(
                            common_template_dir)
                        )
                else:
                    # Ignoring library templates for tree parsing purposes
                    # Removing node from tree
                    children = list(current_node.parent.children)
                    children.remove(current_node)
                    current_node.parent.children = children

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
            fragment_code = glob(os.path.join(self.doc_spec.path,
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
    def setup_logger(doc_metadata, log_level):
        """
        Initializes and sets up the logger.

        :param dict doc_metadata: Document metadata
        :param int log_level: Log level
        """
        logger = logging.getLogger(doc_metadata['logger_name'])
        log_path = doc_metadata['log_path']

        tmp_logs = glob(os.path.join(log_path, '_*'))
        for tmp_log in tmp_logs:
            os.unlink(tmp_log)

        file_handler = logging.FileHandler(
            DocumentCompiler._get_log_file_path(doc_metadata))
        formatter = logging.Formatter(DocumentCompiler.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        logger.setLevel(log_level)
        logger.addHandler(file_handler)

    @staticmethod
    def shutdown_loggers():
        """
        Shutdowns the logger and its handlers.
        """
        loggers = (logger for logger_name, logger
                   in logging.getLogger().manager.loggerDict.items()
                   if logger_name.startswith('reportcompiler.'))

        for logger in loggers:
            handlers = logger.handlers[:]
            for handler in handlers:
                handler.close()
                logger.removeHandler(handler)

    def generate(self,
                 doc_params,
                 doc_metadata,
                 n_doc_workers=2,
                 n_frag_workers=2,
                 debug_mode=False,
                 log_level=logging.DEBUG):
        """
        Generates documents from a list of document variables.

        :param dict doc_params: List of document variables, where each document
            variable is a dictionary with variables associated with a document.
        :param dict doc_metadata: Document metadata
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
            log_level = logging.DEBUG
            self._prepare_debug_session(doc_metadata)

        doc_metadata['debug_mode'] = debug_mode

        doc_info = namedtuple('doc_info', ['doc', 'result', 'exception'])
        results = []
        if n_doc_workers == 1:
            # If there is only one worker, do it in the same process
            # (easier to debug)
            for doc_param in doc_params:
                result = None
                DocumentCompiler.setup_environment(doc_metadata,
                                                   doc_param)
                try:
                    result = self._generate_doc(doc_param,
                                                doc_metadata,
                                                n_frag_workers,
                                                log_level)
                    exception = None
                except Exception as e:
                    exception = e
                info = doc_info(doc=doc_metadata['doc_suffix'],
                                result=result,
                                exception=exception)
                results.append(info)
        else:
            future_results = []
            with ProcessPoolExecutor(max_workers=n_doc_workers) as executor:
                for doc_param in doc_params:
                    _doc_metadata = deepcopy(doc_metadata)
                    DocumentCompiler.setup_environment(_doc_metadata,
                                                       doc_param)
                    worker = self._generate_doc
                    result = executor.submit(worker,
                                             doc_param,
                                             _doc_metadata,
                                             n_frag_workers,
                                             log_level)
                    result.metadata = _doc_metadata
                    future_results.append(result)
                executor.shutdown(wait=True)
            for r in future_results:
                try:
                    result = r.result()
                except Exception as e:
                    result = None
                info = doc_info(doc=r.metadata['doc_suffix'],
                                result=result,
                                exception=r.exception())
                results.append(info)

        DocumentCompiler.shutdown_loggers()

        if debug_mode:
            self._prepare_debug_output(doc_metadata)

        error_results = [r for r in results if r.exception is not None]
        n_errors = len(error_results)
        if n_errors > 0:
            traceback_dict = {}
            for result in error_results:
                error = result.exception
                if isinstance(error, DocumentGenerationError):
                    traceback_dict.update(error.fragment_errors)
                else:
                    error_msg = (str(error) + '\n' +
                                 ''.join(
                                        traceback.format_tb(
                                            error.__traceback__)))
                    traceback_dict.update({result.doc: {
                                            '<global>': (error_msg, None)}})
            raise DocumentGenerationError(
                'Error on document(s) generation:\n', traceback_dict)

    def _prepare_debug_session(self, doc_metadata):
        """
        Actions made before starting the document generation process in debug
        mode.

        :param dict doc_metadata: Document metadata
        """
        meta_dir = os.path.join(doc_metadata['docspec_path'], '..', '_meta')
        for f in glob(os.path.join(meta_dir, 'error_*')):
            os.remove(f)
        if os.path.exists(os.path.join(meta_dir, 'last_debug_errors')):
            os.remove(os.path.join(meta_dir, 'last_debug_errors'))

    def _prepare_debug_output(self, doc_metadata):
        """
        Actions made after finishing the document generation process in debug
        mode.

        :param dict doc_metadata: Document metadata
        """
        meta_dir = os.path.join(doc_metadata['docspec_path'], '..', '_meta')
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

    def _build_final_log(self, doc_logfile_path, doc_metadata):
        """
        When building fragments on parallel processes, this function assembles
        each fragment log into the original one for the document.

        :param str doc_logfile_path: Path to the document log file
        :param dict doc_metadata: Document metadata
        """
        tmp_logs = glob(os.path.join(doc_metadata['log_path'], '_*'))
        with open(doc_logfile_path, 'a') as log:
            log.write('\n--------------')
            log.write('\nFragment logs:')
            log.write('\n--------------\n\n')
            for tmp_log in sorted(tmp_logs):
                with open(tmp_log) as partial_log:
                    log.write(partial_log.read())
                    log.write('------------------------------------------\n\n')
                os.unlink(tmp_log)

    def _generate_fragment(self,
                           fragment,
                           doc_param,
                           doc_metadata,
                           multiprocessing=True,
                           log_level=logging.INFO):
        """
        Returns the context for the current fragment.

        :param str fragment: Fragment name
        :param OrderedDict doc_param: Document variable
        :param dict doc_metadata: Document metadata
        :param bool multiprocessing: Boolean, set to True when using
            multiprocessing
        :param int log_level: Log level
        :returns: (context, path of the fragment)
        :rtype: tuple
        """
        fragment_path = '/'.join([elem.name for elem in fragment.path])
        if self.source_file_map.get(fragment.name):
            current_frag_context = FragmentCompiler.compile(
                self.source_file_map[fragment.name],
                doc_param,
                doc_metadata,
                multiprocessing,
                log_level)
        else:
            current_frag_context = {}
        if not isinstance(current_frag_context, dict):
            current_frag_context = {'data': current_frag_context}
        return current_frag_context, fragment_path

    def _generate_doc(self,
                      doc_param,
                      doc_metadata,
                      n_frag_workers=2,
                      log_level=logging.INFO):
        """
        Generate a document with the specified doc_param.

        :param OrderedDict doc_param: Document variable
        :param dict doc_metadata: Document metadata
        :param int n_frag_workers: Number of concurrent fragment-generating
            threads
        :param int log_level: Log level
        :returns: Document content
        :rtype: str
        """
        DocumentCompiler.setup_logger(doc_metadata, log_level)
        doc_logfile_path = DocumentCompiler._get_log_file_path(doc_metadata)

        try:
            augmented_doc_param = DocumentCompiler.augment_doc_param(
                doc_param, doc_metadata)

            logger = logging.getLogger(doc_metadata['logger_name'])
            logger.info('[{}] Generating document...'.format(
                doc_metadata['doc_suffix']))

            fragment_info = namedtuple('fragment_info', ['fragment',
                                                         'result',
                                                         'exception'])

            sys.path.append(os.path.join(self.doc_spec.path, 'src'))
            if n_frag_workers == 1:
                # If there is only one worker, do it in the same process
                # (easier to debug)
                results = self._generate_doc_fragments_sequential(
                    augmented_doc_param,
                    doc_metadata,
                    fragment_info,
                    log_level)
            else:
                results = self._generate_doc_fragments_parallel(
                    augmented_doc_param,
                    doc_metadata,
                    fragment_info,
                    n_frag_workers,
                    log_level)
            sys.path = sys.path[:-1]

            errors = [r for r in results if r.exception is not None]
            if len(errors) > 0:
                self._raise_doc_generation_errors(results, doc_metadata)

            fragments_context = self._build_fragments_context(results)

            context = self._build_full_context(
                fragments_context, doc_metadata)

            output_doc = DocumentCompiler.render_template(
                augmented_doc_param, context)

            DocumentCompiler.postprocess(
                output_doc,
                augmented_doc_param,
                context)

            logger.info('[{}] Document generated'.format(
                doc_metadata['doc_suffix']))

            return output_doc
        except (DocumentGenerationError,
                TemplateRendererException,
                PostProcessorError) as e:
            logger.error(
                '[{}] Error(s) in document generation, see below'.format(
                    doc_metadata['doc_suffix']))
            raise e from None
        finally:
            if n_frag_workers > 1:
                self._build_final_log(doc_logfile_path, doc_metadata)

        return None

    def _generate_doc_fragments_parallel(self,
                                         augmented_doc_param,
                                         doc_metadata,
                                         fragment_info,
                                         n_frag_workers=1,
                                         log_level=logging.INFO):
        """
        Generate fragment contexts for the current document using parallelism.

        :param OrderedDict augmented_doc_param: Augmented document variable
        :param OrderedDict doc_metadata: Document metadata
        :param namedtuple fragment_info: Named tuple for fragment generation
            info
        :param int n_frag_workers: Number of parallel workers for context
            generation
        :param int log_level: Log level
        :returns: List of results returned by each fragment context generation
        :rtype: list
        """
        results = []
        future_results = []
        with ProcessPoolExecutor(max_workers=n_frag_workers) as executor:
            for fragment in PreOrderIter(self.template_tree.node):
                worker = self._generate_fragment
                result = executor.submit(worker,
                                         fragment,
                                         augmented_doc_param,
                                         doc_metadata,
                                         multiprocessing=True,
                                         log_level=log_level)
                result.fragment = os.path.splitext(fragment.name)[0]
                future_results.append(result)
            executor.shutdown(wait=True)

            for r in future_results:
                try:
                    result = r.result()
                except Exception:
                    result = None
                frag_info = fragment_info(fragment=r.fragment,
                                          result=result,
                                          exception=r.exception())
                results.append(frag_info)
            return results

    def _generate_doc_fragments_sequential(self,
                                           augmented_doc_param,
                                           doc_metadata,
                                           fragment_info,
                                           log_level=logging.INFO):
        """
        Generate fragment contexts for the current document using sequential
        processing.

        :param OrderedDict augmented_doc_param: Augmented document variable
        :param OrderedDict doc_metadata: Document metadata
        :param namedtuple fragment_info: Named tuple for fragment generation
            info
        :param int log_level: Log level
        :returns: List of results returned by each fragment context generation
        :rtype: list
        """
        results = []
        for fragment in PreOrderIter(self.template_tree.node):
            result = None
            try:
                result = self._generate_fragment(fragment,
                                                 augmented_doc_param,
                                                 doc_metadata,
                                                 multiprocessing=False,
                                                 log_level=log_level)
                exception = None
            except Exception as e:
                exception = e
            frag_info = fragment_info(fragment=fragment,
                                      result=result,
                                      exception=exception)
            results.append(frag_info)
        return results

    def _build_full_context(self, fragments_context, doc_metadata):
        context = {'data': fragments_context, 'meta': doc_metadata}

        context['meta']['template_context_info'] = \
            [(
                node.name, '.'.join(
                    [os.path.splitext(path_node.name)[0]
                        for path_node in node.path][1:]))
                for node in PreOrderIter(self.template_tree.node)
             ]
        return context

    def _build_fragments_context(self, fragment_results):
        fragments_context = {}
        for result in fragment_results:
            current_frag_context, fragment_path = result.result
            DocumentCompiler.update_nested_dict(fragments_context,
                                                fragment_path,
                                                current_frag_context)
        return fragments_context

    def _raise_doc_generation_errors(self, results, doc_metadata):
        errors = [r for r in results if r.exception is not None]
        frag_errors = {doc_metadata['doc_suffix']: {}}
        for result in [r
                       for r in results
                       if r.exception is not None]:
            frag_errors[
                    doc_metadata['doc_suffix']][result.fragment] = (
                result.exception.args[0],
                traceback.format_tb(result.exception.__traceback__)
            )
        exception = DocumentGenerationError(
            'Error on fragment(s) generation ({})...'.
            format(len(errors)),
            frag_errors)
        raise exception

    def included_templates(self, content):
        """
        Returns the number of child templates included in content, according
        to the document specification template renderer engine.

        :param str content: String content of the parent template
        :returns: List of child templates included in content
        :rtype: list
        """

        return self.renderer.included_templates(content)

    @staticmethod
    def render_template(doc_param, context):
        """
        Performs the template rendering stage for the document
        (see architecture).

        :param OrderedDict doc_param: Document variable
        :param dict context: Full context with two keys: 'data' for context
            generation output and 'meta' for document metadata
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
        return renderer.render_template(doc_param, context)

    @staticmethod
    def postprocess(doc, doc_param, context):
        """
        Performs the postprocessing stages for the document (see architecture).
        Multiple stages can be defined.

        :param object doc: Document content, output from the template
            rendering stage
        :param OrderedDict doc_param: Document variable
        :param dict context: Full context with two keys: 'data' for context
            generation output and 'meta' for document metadata
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
            postprocessor.postprocess(doc_param,
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
    def augment_doc_param(doc_param, metadata):
        """
        Stage to augment the document variable with necessary additional data
        for the document generation.

        :param OrderedDict doc_param: Document variable
        :param dict metadata: Metadata
        :returns: Document variable "augmented" with the specified additional
            data
        :rtype: dict
        """
        logger = logging.getLogger(metadata['logger_name'])
        message = 'Starting doc_param augmentation...'
        logger.info('[{}] {}'.format(metadata['doc_suffix'], message))
        predata = FragmentCompiler.fetch_info(doc_param,
                                              'params_augmentation',
                                              metadata)
        if len(predata) > 0:
            flattened_predata = dict(ChainMap(*[df.ix[0, :].to_dict()
                                                for df in predata.values()]))
        else:
            flattened_predata = {}
        doc_param.update(flattened_predata)
        return doc_param


class FragmentCompiler:
    """ Class responsible for compiling a fragment within a document """

    @staticmethod
    def setup_logger(fragment_name,
                     doc_metadata,
                     log_level):
        """
        Initializes and sets up the logger.

        :param str fragment_name: Name of the current fragment
        :param dict doc_metadata: Document metadata
        :param int log_level: Log level
        """
        doc_metadata['logger_name'] += '-' + fragment_name
        logger = logging.getLogger(doc_metadata['logger_name'])
        logger.handlers = []
        log_path = doc_metadata['log_path']
        file_handler = logging.FileHandler(
            os.path.join(log_path,
                         '_' +
                         datetime.now().strftime(
                             '%Y_%m_%d__%H_%M_%S') +
                         '__' +
                         doc_metadata['doc_suffix'] +
                         '-' +
                         fragment_name +
                         '.log'))
        formatter = logging.Formatter(DocumentCompiler.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        logger.setLevel(log_level)
        logger.addHandler(file_handler)

    @staticmethod
    def compile(fragment,
                doc_param,
                doc_metadata,
                multiprocessing=True,
                log_level=logging.INFO):
        """
        Compiles a fragment within a document with the given document
        variables.

        :param str fragment: Fragment path from template root
        :param OrderedDict doc_param: Document variable
        :param dict doc_metadata: Document metadata
        :param bool multiprocessing: Boolean, set to True when using
            multiprocessing
        :param int log_level: Log level
        :returns: Context of the specified fragment, to be
            used in the template rendering stage
        :rtype: dict
        """
        metadata = doc_metadata
        metadata['fragment_path'] = fragment
        metadata['fragment_name'] = os.path.splitext(
            os.path.basename(fragment))[0]

        if multiprocessing:
            FragmentCompiler.setup_logger(metadata['fragment_name'],
                                          doc_metadata,
                                          log_level)

        fragment_metadata = FragmentCompiler.retrieve_fragment_metadata(
            doc_param,
            metadata)
        metadata.update(fragment_metadata)
        fragment_data = FragmentCompiler.fetch_data(doc_param,
                                                    metadata)
        context = FragmentCompiler.generate_context(fragment_data,
                                                    doc_param,
                                                    metadata)
        logger = logging.getLogger(metadata['logger_name'])
        logger.info('[{}] {}: Fragment done.\n'.
                    format(metadata['doc_suffix'],
                           metadata['fragment_name']))
        return context

    @staticmethod
    def retrieve_fragment_metadata(doc_param, metadata):
        """
        Stage to extract metadata from within the fragment's source code (see
        architecture).

        :param OrderedDict doc_param: Document variable
        :param dict metadata: Document metadata
        :returns: Fragment metadata dictionary
        :rtype: dict
        """
        _, file_extension = os.path.splitext(metadata['fragment_path'])
        try:
            retriever_name = metadata['source_parser'][file_extension]
            retriever = SourceParser.get(id=retriever_name)
        except KeyError:
            retriever = SourceParser.get(extension=file_extension)
        logger = logging.getLogger(metadata['logger_name'])
        logger.debug(
            '[{}] {}: Retrieving metadata ({})...'.
            format(metadata['doc_suffix'],
                   metadata['fragment_name'],
                   retriever.__class__.__name__))
        return retriever.retrieve_fragment_metadata(doc_param, metadata)

    @staticmethod
    def fetch_data(doc_param, metadata):
        """
        Stage to fetch the data to be used in the context generation stage
        (see architecture).

        :param OrderedDict doc_param: Document variable
        :param dict metadata: Metadata (document metadata, overriden by
            fragment)
        :returns: Pandas dataframe (or list of dataframes) with required data
        :rtype: pandas.DataFrame
        """
        return FragmentCompiler.fetch_info(doc_param, 'data_fetcher', metadata)

    @staticmethod
    def fetch_info(doc_param, fetcher_key, metadata):
        """
        Fetches data according to fetcher_key.

        :param OrderedDict doc_param: Document variable
        :param dict metadata: Metadata (document metadata, overriden by
            fragment)
        :returns: Pandas dataframe (or list of dataframes) with required data
        :rtype: pandas.DataFrame
        """
        fragment_name = metadata.get('fragment_name')
        if fragment_name is None:
            # If it's None, we are fetching data for the document itself
            # (e.g. allowed doc_params)
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
            dt = fetcher.fetch(doc_param, fetcher_info, metadata)
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
    def generate_context(fragment_data, doc_param, metadata):
        """
        Stage to generate dictionary to be used as context for template
        rendering stage.

        :param pandas.DataFrame fragment_data: Pandas dataframe (or list
            of dataframes) with the current fragment's data
        :param OrderedDict doc_param: Document variable
        :param dict metadata: Metadata (document metadata, overriden by
            fragment)
        :returns: Dictionary with the context of the current fragment, to be
            used in the template rendering stage
        :rtype: dict
        """
        logger = logging.getLogger(metadata['logger_name'])
        _, file_extension = os.path.splitext(metadata['fragment_path'])

        generator = None
        try:
            generator_info = metadata['source_parser']
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

        logger.info('[{}] {}: Starting context generation...'.format(
            metadata['doc_suffix'],
            metadata['fragment_name']))
        context = generator.setup_and_generate_context(doc_param,
                                                       fragment_data,
                                                       metadata)
        return context
