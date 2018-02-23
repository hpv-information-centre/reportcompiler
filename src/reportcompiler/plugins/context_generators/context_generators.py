import json
import os
import hashlib
import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import ContextGenerationError


class FragmentContextGenerator(PluginModule):
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
        :return: Dictionary with context for the template rendering stage
        :rtype: dict
        """
        logger = logging.getLogger(metadata['logger'])

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
                        return context
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
                            metadata['fragment_path'],
                            None,
                            metadata,
                            message="[{}] {}: Unexpected error".format(
                                metadata['doc_suffix'],
                                metadata['fragment_name']))

            with open(fragment_hash_basename + '.hash', 'w') as hash_file:
                hash_file.write(current_hash)

        with open(fragment_tmp_basename + '.docvar', 'w') as docvar_file:
            docvar_file.write(json.dumps(doc_var))
            metadata['docvar_file'] = fragment_tmp_basename + '.docvar'

        with open(fragment_tmp_basename + '.data', 'w') as data_file:
            data_file.write(json_data)
            metadata['data_file'] = fragment_tmp_basename + '.data'

        with open(fragment_tmp_basename + '.metadata', 'w') as metadata_file:
            metadata_file.write(json.dumps(metadata))
            metadata['metadata_file'] = fragment_tmp_basename + '.metadata'

        logger.debug(
            '[{}] {}: Generating context ({})...'.format(
                metadata['doc_suffix'],
                metadata['fragment_name'],
                self.__class__.__name__))
        context = self.generate_context(doc_var, data, metadata)

        with open(fragment_hash_basename + '.ctx', 'w') as output_file:
            output_file.write(json.dumps(context, sort_keys=True))

        if (metadata.get('delete_generator_params_files') and
                metadata['delete_generator_params_files']):
            os.remove(fragment_tmp_basename + '.docvar')
            os.remove(fragment_tmp_basename + '.data')
            os.remove(fragment_tmp_basename + '.metadata')

        del metadata['docvar_file']
        del metadata['data_file']
        del metadata['metadata_file']
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
        :return: Dictionary with context for the template rendering stage
        :rtype: dict
        """
        raise NotImplementedError(
            'Context generation not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_generator_exception(cls, filename, exception, context,
                                  message=None):
        """
        Returns a context generation exception with the necessary info
        attached.

        :param str filename: Fragment filename
        :param Exception exception: Exception returned by context generation
        :param dict context: Context for fragment
        :param str message: Optional message for exception
        :raises ContextGenerationError: always
        """
        exception_info = message if message else str(exception)
        full_msg = '{}: Context generation error:\n{}'.format(filename,
                                                              exception_info)
        err = ContextGenerationError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def _get_default_handler(cls, **kwargs):
        """
        In case no explicit plugin is specified, each plugin type can specify
        a default plugin.

        :param dict kwargs: Parameters to decide on a default
        :return: Default plugin
        :rtype: PluginModule
        """
        extension_dict = {
            '.py': FragmentContextGenerator.get('python'),
            '.r': FragmentContextGenerator.get('r')
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

__all__ = ['FragmentContextGenerator', ]
