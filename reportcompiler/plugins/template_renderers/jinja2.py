""" jinja2.py

This module includes the template renderer using jinja2 (and derivatives).

"""

import re
import os
import itertools
import shutil
import anytree
from datetime import datetime
from reportcompiler.plugins.template_renderers.base \
    import TemplateRenderer
from anytree import PreOrderIter

try:
    import jinja2
    from jinja2.exceptions import UndefinedError
except ImportError:
    raise EnvironmentError('Python package "jinja2" needed for '
                           'jinja template renderer')

__all__ = ['JinjaRenderer', 'JinjaLatexRenderer', ]


class JinjaRenderer(TemplateRenderer):
    """ Template renderer for jinja2. """

    def _comment_disabled_templates(self,
                                    fragment_content,
                                    all_included_templates,
                                    jinja_env):
        child_template_info = self.included_templates(
                                            fragment_content)
        for child_name, child_block in child_template_info:
            if child_name not in all_included_templates:
                fragment_content = fragment_content.replace(
                    child_block,
                    '{} {} {}'.format(jinja_env.comment_start_string,
                                      child_block,
                                      jinja_env.comment_end_string)
                )
        return fragment_content

    def render_template(self, doc_param, template_tree, context):
        try:
            template_dirs = []
            template_tmp_dir = os.path.join(
                context['meta']['tmp_path'],
                '_templates')
            if not os.path.exists(template_tmp_dir):
                os.mkdir(template_tmp_dir)
            template_dirs.append(template_tmp_dir)

            lib_path_env = 'RC_TEMPLATE_LIBRARY_PATH'
            if lib_path_env in os.environ:
                template_common_dir = os.environ[
                    'RC_TEMPLATE_LIBRARY_PATH']
                if os.path.exists(template_common_dir):
                    template_dirs.append(template_common_dir)
            environment = self._build_environment(template_dirs)
            self._generate_temp_templates(environment, template_tree, context)
            # TODO: render vs generate
            rendered_template = \
                environment.get_template(
                    context['meta']['main_template']).render(
                        context)

            shutil.rmtree(template_tmp_dir, ignore_errors=True)

            filename = context['meta']['doc_name']
            suffix = context['meta']['doc_suffix']
            if suffix != '':
                filename += '-' + suffix
            tmp_path = context['meta']['tmp_path']
            if context['meta'].get('partial_generation_fragments'):
                filename += '__' + '-'.join(
                    context['meta']['partial_generation_fragments'])
            filename += '.' + self.get_extension(context)
            tex_file = os.path.join(tmp_path, filename)
            with open(tex_file, 'w') as f:
                f.write(rendered_template)

            return filename
        except Exception as e:
            TemplateRenderer.raise_rendering_exception(context, exception=e)

    def _generate_temp_templates(self, env, template_tree, context):
        all_included_templates = anytree.findall(template_tree.node,
                                                 lambda _: True)
        all_included_templates = [n.name for n in all_included_templates]

        for subtree in PreOrderIter(template_tree.node):
            node = subtree
            template_file = node.name
            template_path, _ = os.path.splitext(node.name)
            try:
                with open(os.path.join(context['meta']['tmp_path'],
                                       '_templates',
                                       node.name), 'w') as f_tmp:
                    pass
            except FileNotFoundError:
                full_path = os.path.join(context['meta']['tmp_path'],
                                         '_templates',
                                         node.name)
                os.makedirs(os.path.dirname(full_path))
            try:
                with open(os.path.join(context['meta']['templates_path'],
                                       node.name), 'r') as f_orig, \
                    open(os.path.join(context['meta']['tmp_path'],
                                      '_templates',
                                      node.name), 'w') as f_tmp:
                    content = f_orig.read()

                    content = self._comment_disabled_templates(
                        content, all_included_templates, env)

                    header = self.get_fragment_start_comment(template_file) + \
                        '\n' + env.block_start_string + \
                        'with ctx = {}'.format(
                            'data.' + template_path.replace(os.path.sep, '.')
                            if template_path != ''
                            else 'data') + \
                        env.block_end_string + '\n'
                    header += env.block_start_string + \
                        'with style = meta.style' + \
                        env.block_end_string + '\n'

                    footer = '\n' + \
                             env.block_start_string + \
                             'endwith' + \
                             env.block_end_string
                    footer += '\n' + \
                              env.block_start_string + \
                              'endwith' + \
                              env.block_end_string
                    f_tmp.write(header + content + footer)
            except FileNotFoundError:
                common_template_dir = os.environ['RC_TEMPLATE_LIBRARY_PATH']
                if not os.path.exists(common_template_dir + template_file):
                    raise FileNotFoundError(
                        'Template {} does not exist in document specification '
                        ' nor in the RC_TEMPLATE_LIBRARY_PATH')

    def included_templates(self, content):
        templates = re.findall(pattern='{%.*%}', string=content)
        templates = [t
                     for t
                     in templates if len(re.findall(
                                            pattern='^[ ]*##', string=t)) == 0]

        template_names = [re.findall(
                        pattern=r'\{%[ ]*include[ ]*[\'"](.*?)[\'"][ ]*%\}',
                        string=t) for t in templates]
        template_names = list(itertools.chain.from_iterable(template_names))

        template_blocks = [re.findall(
                        pattern=r'\{%[ ]*include[ ]*[\'"].*?[\'"][ ]*%\}',
                        string=t) for t in templates]
        template_blocks = list(itertools.chain.from_iterable(template_blocks))

        return list(zip(template_names, template_blocks))

    def _build_environment(self, template_dirs):
        jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dirs),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True)

        jinja_env.line_comment_prefix = r'##'

        return jinja_env

    def get_fragment_start_comment(self, name):
        # No markers, since we have no information on the output format
        return ''

    def get_extension(self, context):
        return ''


class JinjaLatexRenderer(JinjaRenderer):
    """ Template renderer for jinja2, with latex-friendly syntax. """

    def _build_environment(self, template_dirs):
        jinja_env = super(JinjaLatexRenderer, self)._build_environment(
            template_dirs)

        def escape_tex(value):
            LATEX_SUBS = (
                (re.compile(r'\\'), r'\\\\'),
                (re.compile(r'([{}_#%&$])'), r'\\\1'),
                (re.compile(r'~'), r'\~{}'),
                (re.compile(r'\^'), r'\^{}'),
                (re.compile(r'"'), r"''"),
                (re.compile(r'\.\.\.+'), r'\\ldots '),
            )

            newval = value
            for pattern, replacement in LATEX_SUBS:
                newval = pattern.sub(replacement, newval)
            return newval

        def escape_path(value):
            return value.replace('\\', '/')

        def format_date(value, new_format):
            return datetime.strptime(value, '%Y-%m-%d').strftime(new_format)

        jinja_env.block_start_string = r'\BLOCK{'
        jinja_env.block_end_string = r'}'
        jinja_env.variable_start_string = r'\VAR{'
        jinja_env.variable_end_string = r'}'
        jinja_env.comment_start_string = r'\COMMENT'
        jinja_env.comment_end_string = r'\ENDCOMMENT'
        jinja_env.line_comment_prefix = r'%#'
        jinja_env.filters['escape_tex'] = escape_tex
        jinja_env.filters['escape_path'] = escape_path
        jinja_env.filters['format_date'] = format_date
        jinja_env.trim_blocks = True
        jinja_env.lstrip_blocks = True
        jinja_env.autoescape = False

        return jinja_env

    def included_templates(self, content):
        jinja_env = self._build_environment(template_dirs=[])
        templates = re.findall(pattern='.*BLOCK.*', string=content)
        templates = [t
                     for t
                     in templates if len(re.findall(
                                            pattern='^[ ]*%#', string=t)) == 0]
        template_names = [re.findall(
                pattern=(jinja_env.block_start_string +
                         r'[ ]*include[ ]*[\'"](.*?)[\'"][ ]*' +
                         jinja_env.block_end_string).replace('\\', '\\\\'),
                string=t) for t in templates]
        template_names = list(itertools.chain.from_iterable(template_names))
        template_names = [tn.replace('/', os.path.sep)
                          for tn in template_names]
        template_blocks = [re.findall(
                pattern=(jinja_env.block_start_string +
                         r'[ ]*include[ ]*[\'"].*?[\'"][ ]*' +
                         jinja_env.block_end_string).replace('\\', '\\\\'),
                string=t) for t in templates]
        template_blocks = list(itertools.chain.from_iterable(template_blocks))

        return list(zip(template_names, template_blocks))

    def get_fragment_start_comment(self, name):
        return r'%%%%%%%%%%%%%%%%% FRAGMENT: {} %%%%%%%%%%%%%%%%%'.format(name)

    def get_extension(self, context):
        return 'tex'
