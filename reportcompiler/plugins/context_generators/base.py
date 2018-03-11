""" base.py

This module includes the base plugin interface for context generators.

"""


import json
import os
import hashlib
import logging
from tempfile import NamedTemporaryFile
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import ContextGenerationError


class ContextGenerator(PluginModule):
    """ Plugin that implements the context generation stage for a fragment. """
    def generate_context_wrapper(self, doc_var, data, metadata):
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

        if (metadata.get('skip_unchanged_fragments') is None or
                not metadata['skip_unchanged_fragments']):
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
                        "[{}] {}: No previous context found, generating...".
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
                            "[{}] {}: {} differ, generating context...".
                            format(metadata['doc_suffix'],
                                   metadata['fragment_name'],
                                   hash_differences_str))
                    elif not os.path.exists(fragment_hash_basename + '.ctx'):
                        logger.info(
                            "[{}] {}: Output data not available".format(
                                metadata['doc_suffix'],
                                metadata['fragment_name']) +
                            ", generating context...")
                    else:
                        self.raise_generator_exception(
                            metadata,
                            message="[{}] {}: Unexpected error".format(
                                metadata['doc_suffix'],
                                metadata['fragment_name']))

            if context is None:
                with open(fragment_hash_basename + '.hash', 'w') as hash_file:
                    hash_file.write(current_hash)

        with open(fragment_tmp_basename + '.json', 'w') as cache_file:
            cache_file.write(json.dumps({'doc_var': doc_var,
                                         'data': json.loads(json_data),
                                         'metadata': metadata}, indent=2))
            metadata['cache_file'] = fragment_tmp_basename + '.json'

        logger.debug(
            '[{}] {}: Generating context ({})...'.format(
                metadata['doc_suffix'],
                metadata['fragment_name'],
                self.__class__.__name__))

        if context is None:  # If context is defined, skip the generation
            try:
                context = self.generate_context(doc_var, data, metadata)
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
                        err_file.write(
                            json.dumps({'doc_var': doc_var,
                                        'data': json.loads(json_data),
                                        'metadata': metadata,
                                        'report': os.path.basename(
                                            metadata['report_path'])},
                                       indent=2))
                raise e from None

        with open(fragment_hash_basename + '.ctx', 'w') as output_file:
            output_file.write(json.dumps(context, sort_keys=True))

        if (metadata.get('delete_generator_files') and
                metadata['delete_generator_files']):
            os.remove(fragment_tmp_basename + '.json')

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
        exception_info = message if message else str(exception)
        if context.get('fragment_path'):
            location = context['fragment_path']
        else:
            location = '<None>'
        full_msg = '{}: Context generation error:\n{}'.format(location,
                                                              exception_info)
        if context.get('logger_name'):
            logger = logging.getLogger(context['logger_name'])
            logger.error('[{}] {}'.format(context['doc_suffix'], full_msg))
        err = ContextGenerationError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def _get_default_handler(cls, **kwargs):
        extension_dict = {
            '.py': ContextGenerator.get('python'),
            '.r': ContextGenerator.get('r')
        }
        try:
            extension = kwargs['extension']
        except KeyError:
            raise ValueError('File extension not specified')

        try:
            return extension_dict[extension.lower()]
        except KeyError:
            raise NotImplementedError(
                'No {} specified and no default is available for extension {}'.
                format(cls, extension))

__all__ = ['ContextGenerator', ]
