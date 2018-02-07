import json
import os
import hashlib
import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import ContextGenerationError


class FragmentContextGenerator(PluginModule):
    def generate_context_wrapper(self, doc_var, data, metadata):
        logger = logging.getLogger(metadata['logger'])

        doc_suffix = metadata['doc_suffix']
        fragment_tmp_basename = os.path.join(metadata['tmp_path'],
                                             doc_suffix + '_' + metadata['fragment_name'])
        fragment_hash_basename = os.path.join(metadata['hash_path'],
                                              doc_suffix + '_' + metadata['fragment_name'])

        if isinstance(data, dict):
            json_data = "{" + \
                        ", ".join(['"' + key + '": ' + df.to_json(orient='records') for key, df in data.items()]) + \
                        "}"
        else:
            json_data = data.to_json(orient='records')

        if metadata.get('skip_unchanged_fragments') is None or not metadata['skip_unchanged_fragments']:
            with open(metadata['fragment_path'], 'rb') as f:
                code_hash = hashlib.sha256(f.read()).hexdigest()

            docvar_hash = hashlib.sha256(json.dumps(doc_var, sort_keys=True).encode('utf-8')).hexdigest()
            data_hash = hashlib.sha256(json_data.encode('utf-8')).hexdigest()
            metadata_hash = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode('utf-8')).hexdigest()

            try:
                with open(fragment_hash_basename + '.hash', 'r') as prev_hash_file:
                    previous_hash = prev_hash_file.read()
            except FileNotFoundError:
                previous_hash = ''  # Invalid hash, will not match

            hash_components = [code_hash, docvar_hash, data_hash, metadata_hash]
            hash_component_names = ['code_hash', 'docvar_hash', 'data_hash', 'metadata_hash']
            current_hash = '\n'.join(hash_components)
            if current_hash == previous_hash and os.path.exists(fragment_hash_basename + '.ctx'):
                try:
                    with open(fragment_hash_basename + '.ctx') as f:
                        context = json.load(f)
                        return context
                except FileNotFoundError:
                    pass  # No previous hash available, we run the code
            else:
                if previous_hash == '':
                    logger.warning("[{}] {}: No previous context found, generating...".format(
                        metadata['doc_suffix'],
                        metadata['fragment_name']))
                else:
                    hash_list = current_hash.split('\n')
                    prev_hash_list = previous_hash.split('\n')
                    hash_differences = [hash_list[i] != prev_hash_list[i] for i in range(len(hash_list))]
                    hash_differences = zip(hash_component_names, hash_differences)
                    hash_differences = [component for component, is_different in hash_differences if is_different]
                    hash_differences_str = ', '.join(hash_differences)
                    if len(hash_differences) > 0:
                        logger.warning("[{}] {}: {} differ, generating context...".format(metadata['doc_suffix'],
                                                                                          metadata['fragment_name'],
                                                                                          hash_differences_str))
                    elif not os.path.exists(fragment_hash_basename + '.ctx'):
                        logger.info("[{}] {}: Output data not available, generating context...".format(
                            metadata['doc_suffix'],
                            metadata['fragment_name']))
                    else:
                        self.raise_generator_exception(metadata['fragment_path'],
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

        logger.debug('[{}] {}: Generating context ({})...'.format(metadata['doc_suffix'],
                                                                  metadata['fragment_name'],
                                                                  self.__class__.__name__))
        context = self.generate_context(doc_var, data, metadata)

        with open(fragment_hash_basename + '.ctx', 'w') as output_file:
            output_file.write(json.dumps(context, sort_keys=True))

        if metadata.get('delete_generator_params_files') and metadata['delete_generator_params_files']:
            os.remove(fragment_tmp_basename + '.docvar')
            os.remove(fragment_tmp_basename + '.data')
            os.remove(fragment_tmp_basename + '.metadata')

        del metadata['docvar_file']
        del metadata['data_file']
        del metadata['metadata_file']
        return context

    @abstractmethod
    def generate_context(self, doc_var, data, metadata):
        raise NotImplementedError('Context generation not implemented for {}'.format(self.__class__))

    @classmethod
    def raise_generator_exception(cls, filename, exception, context, message=None):
        exception_info = message if message else str(exception)
        full_msg = '{}: Context generation error:\n{}'.format(filename, exception_info)
        err = ContextGenerationError(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

    @classmethod
    def _get_default_handler(cls, extension):
        extension_dict = {
            '.py': FragmentContextGenerator.get('python'),
            '.r': FragmentContextGenerator.get('r')
        }
        try:
            return extension_dict[extension]
        except KeyError:
            raise NotImplementedError('No {} specified and no default is available for extension {}'.format(cls,
                                                                                                            extension))
