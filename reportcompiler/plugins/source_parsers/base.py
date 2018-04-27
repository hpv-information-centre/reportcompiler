""" base.py

This module includes the base plugin interface for context generators.

"""

import json
import os
import hashlib
import logging
import traceback
import time
from datetime import datetime
from tempfile import NamedTemporaryFile
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import \
    ContextGenerationError, MetadataRetrievalError

__all__ = ['SourceParser', ]


class SourceParser(PluginModule):
    """ Plugin that implements the parsing for source files: the metadata
    retrieval and the context generation stages for a fragment. """

    entry_point_group = 'source_parsers'

    def setup_and_generate_context(self, doc_var, data, metadata):
        """
        Wraps the context generation with temporary file creation and hash
        checking to avoid unnecessary processing.

        :param OrderedDict doc_var: Document variable
        :param pandas.DataFrame data: Dataframe (or list of dataframes)
            with the specified input data
        :param dict metadata: Report metadata (overriden by fragment metadata
            when specified)
        :returns: Dictionary with context for the template rendering stage
        :rtype: dict
        """
        logger = logging.getLogger(metadata['logger_name'])

        doc_suffix = metadata['doc_suffix']
        fragment_tmp_basename = os.path.join(metadata['tmp_path'],
                                             doc_suffix + '_' +
                                             metadata['fragment_name'])
        fragment_hash_basename = os.path.join(metadata['hash_path'],
                                              doc_suffix + '_' +
                                              metadata['fragment_name'])

        if isinstance(data, dict):
            json_data = "{" + \
                        ", ".join(
                            ['"' + key + '": ' + df.to_json(orient='records')
                                for key, df
                                in data.items()]
                            ) + \
                        "}"
        else:
            json_data = data.to_json(orient='records')

        if metadata['skip_unchanged_fragments']:
            context = None
            with open(metadata['fragment_path'], 'rb') as f:
                code_hash = hashlib.sha256(f.read()).hexdigest()

            docvar_hash = hashlib.sha256(
                json.dumps(doc_var, sort_keys=True).encode('utf-8')
                ).hexdigest()
            data_hash = hashlib.sha256(json_data.encode('utf-8')).hexdigest()
            metadata_hash = hashlib.sha256(
                json.dumps(metadata, sort_keys=True).encode('utf-8')
                ).hexdigest()

            try:
                with open(fragment_hash_basename + '.hash', 'r') \
                        as prev_hash_file:
                    previous_hash = prev_hash_file.read()
            except FileNotFoundError:
                previous_hash = ''  # Invalid hash, will not match

            hash_components = [code_hash, docvar_hash,
                               data_hash, metadata_hash]
            hash_component_names = ['code_hash', 'docvar_hash',
                                    'data_hash', 'metadata_hash']
            current_hash = '\n'.join(hash_components)
            if (current_hash == previous_hash and
                    os.path.exists(fragment_hash_basename + '.ctx')):
                try:
                    with open(fragment_hash_basename + '.ctx') as f:
                        context = json.load(f)
                except FileNotFoundError:
                    pass  # No previous hash available, we run the code
            else:
                if previous_hash == '':
                    logger.warning(
                        "[{}] {}: No previous context found, regenerating...".
                        format(metadata['doc_suffix'],
                               metadata['fragment_name']))
                else:
                    hash_list = current_hash.split('\n')
                    prev_hash_list = previous_hash.split('\n')
                    hash_differences = [hash_list[i] != prev_hash_list[i]
                                        for i in range(len(hash_list))]
                    hash_differences = zip(hash_component_names,
                                           hash_differences)
                    hash_differences = [component
                                        for component, is_different
                                        in hash_differences
                                        if is_different]
                    hash_differences_str = ', '.join(hash_differences)
                    if len(hash_differences) > 0:
                        logger.warning(
                            "[{}] {}: {} differ, regenerating context...".
                            format(metadata['doc_suffix'],
                                   metadata['fragment_name'],
                                   hash_differences_str))
                    elif not os.path.exists(fragment_hash_basename + '.ctx'):
                        logger.info(
                            "[{}] {}: Output data not available".format(
                                metadata['doc_suffix'],
                                metadata['fragment_name']) +
                            ", regenerating context...")
                    else:
                        self.raise_generator_exception(
                            metadata,
                            message="[{}] {}: Unexpected error".format(
                                metadata['doc_suffix'],
                                metadata['fragment_name']))

        with open(fragment_tmp_basename + '.json', 'w') as cache_file:
            cache_file.write(json.dumps({'doc_var': doc_var,
                                         'data': json.loads(json_data),
                                         'metadata': metadata}, indent=2))
            metadata['cache_file'] = fragment_tmp_basename + '.json'

        if context is None:  # If context is defined, skip the generation
            try:
                context = self.generate_context(doc_var, data, metadata)

                if metadata['skip_unchanged_fragments']:
                    with open(fragment_hash_basename + '.hash', 'w') as hash_f:
                        hash_f.write(current_hash)
            except Exception as e:
                meta_dir = os.path.join(metadata['report_path'],
                                        '..',
                                        '_meta')
                if metadata['debug_mode']:
                    if not os.path.exists(meta_dir):
                        os.mkdir(meta_dir)
                    with NamedTemporaryFile(dir=meta_dir,
                                            prefix='error_',
                                            delete=False,
                                            mode='w') \
                            as err_file:
                        ts = time.time()
                        timestamp = datetime.fromtimestamp(ts).strftime(
                            '%Y-%m-%d %H:%M:%S')
                        err_file.write(
                            json.dumps({'timestamp': timestamp,
                                        'doc_var': doc_var,
                                        'data': json.loads(json_data),
                                        'metadata': metadata,
                                        'report': os.path.basename(
                                            metadata['report_path'])},
                                       indent=2))
                raise e from None
        else:
            logger.info(
                '[{}] {}: Same input, reusing previous context ({})...'
                .format(
                    metadata['doc_suffix'],
                    metadata['fragment_name'],
                    self.__class__.__name__))

        with open(fragment_hash_basename + '.ctx', 'w') as output_file:
            output_file.write(json.dumps(context, sort_keys=True))

        del metadata['cache_file']
        return context

    @abstractmethod
    def generate_context(self, doc_var, data, metadata):
        """
        Generates the dictionary context.

        :param OrderedDict doc_var: Document variable
        :param pandas.DataFrame data: Pandas dataframe (or list of dataframes)
            with the specified input data
        :param dict metadata: Report metadata (overriden by fragment metadata
            when specified)
        :returns: Dictionary with context for the template rendering stage
        :rtype: dict
        """
        raise NotImplementedError(
            'Context generation not implemented for {}'.format(self.__class__))

    @abstractmethod
    def retrieve_fragment_metadata(self, doc_var, metadata):
        """
        Retrieves the metadata required to process the fragment.

        :param OrderedDict doc_var: Document variable
        :param dict metadata: Report metadata (overriden by fragment metadata
            when specified)
        :returns: Dictionary with metadata
        :rtype: dict
        """
        raise NotImplementedError(
            'Metadata retrieval not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_generator_exception(cls, context, exception=None,
                                  message=None):
        """
        Returns a context generation exception with the necessary info
        attached.

        :param dict context: Context for fragment
        :param Exception exception: Exception returned by context generation
        :param str message: Optional message for exception
        :raises ContextGenerationError: always
        """
        exception_info = (message
                          if message
                          else ''.join(
                              traceback.format_tb(exception.__traceback__)))
        if context.get('fragment_name'):
            location = context['fragment_name']
        else:
            location = '<None>'
        exception_type = type(exception).__name__
        full_msg = '{}: Context generation error ({}): {}\n{}\n'.format(
            location,
            exception_type,
            str(exception) if exception_type != 'CalledProcessError' else '',
            exception_info)
        if context.get('logger_name'):
            logger = logging.getLogger(context['logger_name'])
            logger.error('[{}] {}'.format(context['doc_suffix'], full_msg))
        err = ContextGenerationError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def raise_retriever_exception(cls, context, exception=None,
                                  message=None):
        """
        Returns a metadata retrieval exception with the necessary info
        attached.

        :param dict context: Context for fragment
        :param Exception exception: Exception returned by metadata retrieval
        :param str message: Optional message for exception
        :raises MetadataRetrievalError: always
        """
        exception_info = message if message else '    ' + str(exception)
        if context.get('fragment_name'):
            location = context['fragment_name']
        else:
            location = '<None>'
        full_msg = '{}: Metadata retrieval error:\n{}\n'.format(
            location,
            exception_info)
        if context.get('logger_name'):
            logger = logging.getLogger(context['logger_name'])
            logger.error('[{}] {}'.format(context['doc_suffix'], full_msg))
        err = MetadataRetrievalError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def _get_default_handler(cls, **kwargs):
        extension_dict = {
            '.py': 'python',
            '.r': 'r'
        }
        try:
            extension = kwargs['extension']
        except KeyError:
            raise ValueError('File extension not specified')

        try:
            return SourceParser.get(extension_dict[extension.lower()])
        except KeyError:
            raise NotImplementedError(
                'No {} specified and no default is available for extension {}'.
                format(cls, extension))
