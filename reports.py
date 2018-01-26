import json
import os
import re
from collections import OrderedDict
from glob import glob
import sys
import logging
from datetime import datetime
from jsmin import jsmin
from copy import deepcopy
from collections import ChainMap
import git
from git import GitCommandError, InvalidGitRepositoryError
import pandas as pd

from django.conf import settings
from reportcompiler.plugins.data_fetchers.data_fetchers import FragmentDataFetcher
from reportcompiler.plugins.context_generators.context_generators import FragmentContextGenerator
from reportcompiler.plugins.metadata_retriever.metadata_retriever import FragmentMetadataRetriever
from reportcompiler.plugins.template_renderers.template_renderers import TemplateRenderer
from reportcompiler.plugins.postprocessors.postprocessors import PostProcessor


class Report:
    # TODO: KEYWORD!!!
    GIT_PROJECTS_PATH = 'I:/d_gomez/reports'

    def __init__(self, directory=None, repo_url=None):
        if not directory and not repo_url:
            raise ValueError("'directory' or 'repo' must be specified")
        if repo_url:
            repo_name, _ = os.path.splitext(os.path.basename(repo_url))
            repo_path = os.path.join(Report.GIT_PROJECTS_PATH, repo_name)
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
        # config = configparser.ConfigParser()
        # config.read(config_file)

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
        # 	print("Warning: some source files don't have corresponding templates: {}".format(', '.join(dangling_sources)))
        # dangling_templates = templates.difference(source)
        # if len(dangling_templates) > 0:
        # 	print("Warning: some templates don't have corresponding source files: {}".format(', '.join(dangling_templates)))

        if not os.path.exists('{}/templates/{}'.format(self.path, self.config['main_template'])):
            raise FileNotFoundError("Main template defined in config.ini () doesn't exist".format(self.config['main_template']))

    def __str__(self):
        return self.verbose_name

    @property
    def templates(self):
        return os.listdir('{}/templates'.format(self.path))

    @property
    def source_code(self):
        return os.listdir('{}/src'.format(self.path))

    @property
    def main_template(self):
        return self.config['main_template']

    def generate(self, doc_vars = {}, debug_level = logging.DEBUG):
        if not isinstance(doc_vars, list): doc_vars = [doc_vars]
        # Check for mandatory variables
        mandatory_vars = self.config.get('mandatory_doc_vars')
        if not mandatory_vars:
            mandatory_vars = []
        mandatory_vars = set(mandatory_vars)
        for doc_var in doc_vars:
            current_var_keys = set(doc_var.keys())
            if not mandatory_vars.issubset(current_var_keys):
                missing_vars = mandatory_vars - current_var_keys
                raise ValueError('Some mandatory document variables were not specified: {}\nVariables set: {}'.format(', '.join(missing_vars), doc_var))

        report_metadata = OrderedDict(self.config)
        report_metadata['report_path'] = self.path
        for doc_var in doc_vars:
            # Deep copy to avoid concurrency issues in parallel computation
            report_metadata_copy = deepcopy(report_metadata)
            self._setup_paths(report_metadata_copy, doc_var)
            compiler = ReportCompiler(self)
            doc = compiler.generate(doc_var, report_metadata_copy, debug_level=debug_level)
        return None

    def _setup_paths(self, metadata, doc_var):
        def _build_subpath(directory):
            return os.path.join(metadata['report_path'], 'gen', metadata['doc_suffix'], directory)

        metadata['doc_suffix'] = ReportCompiler.get_doc_var_suffix(doc_var)
        dirs = ['fig', 'hash', 'log', 'tmp', 'out']
        for d in dirs:
            metadata['{}_path'.format(d)] = _build_subpath(d)
            if not os.path.exists(metadata['{}_path'.format(d)]):
                os.makedirs(metadata['{}_path'.format(d)], os.O_RDWR)
        metadata['data_path'] = os.path.join(metadata['report_path'], 'data')
        metadata['logger'] = metadata['name'] + '_' + metadata['doc_suffix']


class ReportCompiler:
    LOG_FORMAT = '%(asctime)-15s %(message)s'

    @staticmethod
    def get_doc_var_suffix(doc_var):
        try:
            if isinstance(doc_var, list) or isinstance(doc_var, tuple):
                suffix = '-'.join([str(v) for v in doc_var])
            elif isinstance(doc_var, dict):
                suffix = '-'.join([str(v) for v in list(doc_var.values())])
            elif isinstance(doc_var, str):
                suffix = doc_var
            return suffix
        except KeyError:
            return ''

    def __init__(self, report):
        self.report = report
        self.generate_fragments_mapping()

    def generate_fragments_mapping(self):
        '''
        Finds fragments used by the report self.report.
        TODO: Detect commented fragments and leave them out
        '''

        # Fragment stack with tuple elements (fragment_name, fragment_parent_path)
        stack = [(self.report.main_template, '')]
        fragments = set(stack)
        # TODO: Support for subdirectories
        while len(stack) > 0:
            current_fragment, current_fragment_path = stack.pop()
            with open(os.path.join(self.report.path, 'templates', current_fragment)) as f:
                content = f.read()
            # fragments_found = re.findall(pattern=self.included_templates_regex(), string=content)
            fragments_found = self.included_templates(content)
            new_fragments = set(fragments_found).difference(fragments)
            new_fragments_info = [(f, current_fragment_path + '/' + current_fragment) if current_fragment_path != '' else (f, current_fragment) for f in new_fragments]
            # new_fragments_info_no_ext = [(os.path.splitext(f)[0], p) for f, p in new_fragments_info]
            stack.extend(new_fragments_info)
            fragments = fragments.union(new_fragments_info)

        src_fragments_dict = {}
        src_fragments = []
        for fragment, fragment_path in fragments:
            fragment_basename, _ = os.path.splitext(fragment)
            fragment_code = glob(os.path.join(self.report.path, 'src', '{}.[a-zA-Z0-9]*'.format(fragment_basename)))
            if len(fragment_code) == 0:
                print('Warning: no source file for template "{}", context will be empty.'.format(fragment_basename))
            elif len(fragment_code) > 1:
                # No multiple files with same name but different extensions allowed
                raise EnvironmentError('More than one source file for fragment {}'.format(fragment_basename))
            # src_fragments_dict = path_to_tree_dict(src_fragments_dict, fragment_path + '/' + fragment if fragment_path != '' else fragment)
            else:
                full_fragment_path = fragment_path + '/' + fragment if fragment_path != '' else fragment
                src_fragments.append(full_fragment_path)
                src_fragments_dict[fragment] = fragment_code[0] # Guaranteed to be only one
        self.used_fragments = sorted(src_fragments)
        self.fragment_source_file = src_fragments_dict

    def _setup_logger(self, report_metadata, debug_level):
        logger = logging.getLogger(report_metadata['logger'])
        log_path = report_metadata['log_path']
        file_handler = logging.FileHandler(os.path.join(log_path,
                                                           report_metadata['doc_suffix'] + '__' + datetime.now().strftime('%Y_%m_%d_%H_%M') + '.log'))
        formatter = logging.Formatter(ReportCompiler.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(debug_level)
        return logger

    def generate(self, doc_var, report_metadata, debug_level=logging.DEBUG):
        logger = self._setup_logger(report_metadata, debug_level)
        logger.info('[{}] Generating document...'.format(ReportCompiler.get_doc_var_suffix(doc_var)))
        fragment_compiler = FragmentCompiler(self.report.name, self.report.path)
        fragments_context = {}
		
        sys.path.append(os.path.join(self.report.path,'src'))
        for fragment in self.used_fragments:
            # Deep copy to avoid concurrency issues in parallel computation
            doc_var = deepcopy(doc_var)
            report_metadata = deepcopy(report_metadata)
            current_frag_context = fragment_compiler.compile(self.fragment_source_file[os.path.basename(fragment)], doc_var, report_metadata)
            if not isinstance(current_frag_context, dict):
                current_frag_context = {'data': current_frag_context}
            self._update_nested_dict(fragments_context, fragment, current_frag_context)
        context = {'data': fragments_context, 'meta': report_metadata}
        sys.path = sys.path[:-1]

        if report_metadata.get('generate_context_file') and report_metadata['generate_context_file']:
            logger.info('[{}] Generating context file...'.format(ReportCompiler.get_doc_var_suffix(doc_var)))
            suffix = report_metadata['doc_suffix']
            file_name = 'document.json' if suffix == '' else suffix + '.json'
            with open(os.path.join(report_metadata['tmp_path'], file_name), 'w') as f:
                f.write(json.dumps(context, indent=2, sort_keys=True))

        output_doc = self.render_template(doc_var, context)
        self.postprocess(self.report.path, output_doc, doc_var, context)
        logger.info('[{}] Document generated'.format(ReportCompiler.get_doc_var_suffix(doc_var)))
        return output_doc

    def included_templates_regex(self):
        try:
            renderer = TemplateRenderer.get(id=self.report.config['template_renderer'])
        except KeyError:
            renderer = TemplateRenderer.get() # Default renderer

        return renderer.included_templates_regex()

    def included_templates(self, content):
        try:
            renderer = TemplateRenderer.get(id=self.report.config['template_renderer'])
        except KeyError:
            renderer = TemplateRenderer.get() # Default renderer

        return renderer.included_templates(content)

    def render_template(self, doc_var, context):
        try:
            renderer = TemplateRenderer.get(
                id=context['meta']['template_renderer'])
        except KeyError:
            renderer = TemplateRenderer.get() # Default renderer

        logger = logging.getLogger(context['meta']['logger'])
        logger.debug('[{}] Rendering template ({})...'.format(ReportCompiler.get_doc_var_suffix(doc_var), renderer.__class__.__name__))
        return renderer.render_template(os.path.join(self.report.path,'templates'), self.report.main_template, doc_var, context)

    def postprocess(self, path, doc, doc_var, context):
        try:
            postprocessors_info = context['meta']['postprocessor']
            if not isinstance(postprocessors_info, list):
                postprocessors_info = [postprocessors_info]
        except KeyError:
            postprocessors_info = []

        for postprocessor_info in postprocessors_info:
            postprocessor = PostProcessor.get(id=postprocessor_info)
            logger = logging.getLogger(context['meta']['logger'])
            logger.debug('[{}] Postprocessing ({})...'.format(ReportCompiler.get_doc_var_suffix(doc_var), postprocessor.__class__.__name__))
            postprocessor.postprocess(doc_var, doc, path, postprocessor_info, context)

    def _update_nested_dict(self, doc_context, fragment, frag_context):
        head, tail = os.path.split(fragment)
        fragment_items = []
        while head != '':
            tail_name, tail_extension = os.path.splitext(tail)
            fragment_items.append(tail_name)
            head, tail = os.path.split(head)
        fragment_items.reverse()

        aux_dict = doc_context
        for item in fragment_items:
            if not aux_dict.get(item):
                aux_dict[item] = {}
            aux_dict = aux_dict[item]
        aux_dict.update(frag_context)


class FragmentCompiler:
    def __init__(self, report_name, report_path, **kwargs):
        self.report_name = report_name
        self.report_path = report_path
        if kwargs.get('context_generator_engine'):
            self.context_generator_engine = kwargs['context_generator_engine']

    def compile(self, fragment, doc_var, report_metadata):
        metadata = report_metadata
        metadata['fragment_path'] = fragment
        metadata['fragment_name'] = os.path.splitext(os.path.basename(fragment))[0]

        fragment_metadata = self.retrieve_fragment_metadata(doc_var, metadata)
        metadata.update(fragment_metadata)
        doc_var_augmented = self.prefetch_data(doc_var, metadata)
        fragment_data = self.fetch_data(doc_var_augmented, metadata)
        return self.generate_context(fragment_data, doc_var_augmented, metadata)

    def retrieve_fragment_metadata(self, doc_var, metadata):
        filename, file_extension = os.path.splitext(metadata['fragment_path'])
        try:
            retriever_name = metadata['metadata_retriever'][file_extension]
            retriever = FragmentMetadataRetriever.get(id=retriever_name)
        except KeyError:
            retriever = FragmentMetadataRetriever.get(extension=file_extension)
        logger = logging.getLogger(metadata['logger'])
        logger.debug('[{}] {}: Retrieving metadata ({})...'.format(ReportCompiler.get_doc_var_suffix(doc_var), metadata['fragment_name'], retriever.__class__.__name__))
        return retriever.retrieve_fragment_metadata(doc_var, metadata)

    def prefetch_data(self, doc_var, metadata):
        try:
            prefetchers_info = metadata['predata_fetcher']
        except KeyError:
            prefetchers_info = [] # No prefetchers specified

        if not isinstance(prefetchers_info, list):
            prefetchers_info = [prefetchers_info]

        predata = []
        for i, prefetcher_info in enumerate(prefetchers_info):
            prefetcher = FragmentDataFetcher.get(id=prefetcher_info)
            logger = logging.getLogger(metadata['logger'])
            logger.debug('[{}] {} Prefetching data ({})...'.format(ReportCompiler.get_doc_var_suffix(doc_var), metadata['fragment_name'], prefetcher.__class__.__name__))
            predata.append(prefetcher.fetch(doc_var, prefetcher_info, metadata))

        for datum in predata:
            if len(datum.index) > 1:
                message = '{}: Pre-Data fetcher returning more than one row'.format(metadata['fragment_path'])
                logger = logging.getLogger(metadata['logger'])
                logger.error('[{}] {}'.format(ReportCompiler.get_doc_var_suffix(doc_var), message))
                raise ValueError(message)

        flattened_predata = dict(ChainMap(*[df.ix[0,:].to_dict() for df in predata]))
        flattened_predata.update(doc_var)

        return flattened_predata

    def fetch_data(self, doc_var, metadata):
        try:
            fetchers_info = metadata['data_fetcher']
        except KeyError:
            message = '{}: Data fetcher not specified'.format(metadata['fragment_path'])
            logger = logging.getLogger(metadata['logger'])
            logger.error('[{}] {}'.format(ReportCompiler.get_doc_var_suffix(doc_var), message))
            raise NotImplementedError(message)

        if not isinstance(fetchers_info, list):
            fetchers_info = [fetchers_info]

        data = OrderedDict()
        for i, fetcher_info in enumerate(fetchers_info):
            fetcher = FragmentDataFetcher.get(id=fetcher_info)
            logger = logging.getLogger(metadata['logger'])
            logger.debug('[{}] {} Fetching data ({})...'.format(ReportCompiler.get_doc_var_suffix(doc_var), metadata['fragment_name'], fetcher.__class__.__name__))
            dt = fetcher.fetch(doc_var, fetcher_info, metadata)
            if fetcher_info.get('id') is None:
                fetcher_id = str(i)
            else:
                fetcher_id = fetcher_info['id']
            if data.get('fetcher_id') is not None:
                message = 'Data fetcher id is duplicated {}'.format(fetcher_id)
                logger.error('[{}] {}'.format(ReportCompiler.get_doc_var_suffix(doc_var), message))
                raise NotImplementedError(message)
            data[fetcher_id] = dt

        if len(data) == 0:
            data = pd.DataFrame()
        elif len(data) == 1:
            data = list(data)[0]

        return data

    def generate_context(self, fragment_data, doc_var, metadata):
        logger = logging.getLogger(metadata['logger'])
        filename, file_extension = os.path.splitext(metadata['fragment_path'])

        generator = None
        try:
            generator_info = metadata['context_generator']
            if isinstance(generator_info, str):
                generator = FragmentContextGenerator.get(id=generator_info)
            elif isinstance(generator_info, dict):
                generator = FragmentContextGenerator.get(id=generator_info[file_extension])
            else:
                pass # Context generator invalid, ignoring...
        except KeyError:
            pass

        if not generator:
            try:
                generator = FragmentContextGenerator.get(extension=file_extension)
            except KeyError:
                message = 'Data fetcher not specified for fragment {}'.format(metadata['fragment_name'])
                logger.error('[{}] {}'.format(ReportCompiler.get_doc_var_suffix(doc_var), message))
                raise NotImplementedError(message)
        context = generator.generate_context_wrapper(doc_var, fragment_data, metadata)
        return context


if __name__ == '__main__':
    report = Report('C:\\Users\\47873315B\\Dropbox\\ICO\\ReportCompiler\\reports\\FactSheetTest')
    # report = Report(repo_url='http://icosrvprec02/gitlab/informationcenter/report_factsheet-test.git')
    report.generate([{'iso': 'AUS'}])
