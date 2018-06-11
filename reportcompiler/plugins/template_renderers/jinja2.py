""" jinja2.py

This module includes the template renderer using jinja2 (and derivatives).

"""

import re
import os
import itertools
import shutil
from reportcompiler.plugins.template_renderers.base \
    import TemplateRenderer

try:
    import jinja2
    from jinja2.exceptions import UndefinedError
except ImportError:
    raise TemplateRenderer.raise_rendering_exception(
        metadata,
        message='Python package "jinja2" needed for jinja template renderer')

__all__ = ['JinjaRenderer', 'JinjaLatexRenderer', ]


class JinjaRenderer(TemplateRenderer):
    """ Template renderer for jinja2. """

    def render_template(self, doc_param, context):
        try:
            template_dirs = []
            template_tmp_dir = os.path.join(
                context['meta']['tmp_path'],
                'templates')
            if not os.path.exists(template_tmp_dir):
                os.mkdir(template_tmp_dir)
            template_dirs.append(template_tmp_dir)

            template_common_dir = os.environ[
                'RC_TEMPLATE_LIBRARY_PATH']
            if os.path.exists(template_common_dir):
                template_dirs.append(template_common_dir)
            environment = self._build_environment(template_dirs)
            self._generate_temp_templates(environment, context)
            # TODO: render vs generate
            rendered_template = \
                environment.get_template(
                    context['meta']['main_template']).render(
                        context)

            shutil.rmtree(template_tmp_dir, ignore_errors=True)

            return rendered_template
        except Exception as e:
            TemplateRenderer.raise_rendering_exception(context, exception=e)

    def _generate_temp_templates(self, env, context):
        context_info = context['meta']['template_context_info']
        for template_file, dict_path in context_info:
            try:
                with open(os.path.join(context['meta']['templates_path'],
                                       template_file), 'r') as f_orig, \
                    open(os.path.join(context['meta']['tmp_path'],
                                      'templates',
                                      template_file), 'w') as f_tmp:
                    content = f_orig.read()
                    header = self.get_fragment_start_comment(template_file) + \
                        '\n' + env.block_start_string + \
                        'with ctx = {}'.format(
                            'data.' + dict_path
                            if dict_path != ''
                            else 'data') + \
                        env.block_end_string + '\n'
                    footer = '\n' + \
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
        environment = self._build_environment(template_dirs=[])
        templates = re.findall(pattern='{%.*%}', string=content)
        templates = [t
                     for t
                     in templates if len(re.findall(
                                            pattern='^[ ]*##', string=t)) == 0]
        templates = [re.findall(
                        pattern=r'\{%[ ]*include[ ]*[\'"](.*?)[\'"][ ]*%\}',
                        string=t) for t in templates]
        templates = list(itertools.chain.from_iterable(templates))
        return templates

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
                (re.compile(r'_'), r'\_'),
            )

            newval = value
            for pattern, replacement in LATEX_SUBS:
                newval = pattern.sub(replacement, newval)
            return newval

        def escape_path(value):
            return value.replace('\\', '/')

        jinja_env.block_start_string = r'\BLOCK{'
        jinja_env.block_end_string = r'}'
        jinja_env.variable_start_string = r'\VAR{'
        jinja_env.variable_end_string = r'}'
        jinja_env.comment_start_string = r'\COMMENT'
        jinja_env.comment_end_string = r'\ENDCOMMENT'
        jinja_env.line_comment_prefix = r'%#'
        jinja_env.filters['escape_tex'] = escape_tex
        jinja_env.filters['escape_path'] = escape_path
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
        templates = [re.findall(
                pattern=(jinja_env.block_start_string +
                         r'[ ]*include[ ]*[\'"](.*?)[\'"][ ]*' +
                         jinja_env.block_end_string),
                string=t) for t in templates]
        templates = list(itertools.chain.from_iterable(templates))
        return templates

    def get_fragment_start_comment(self, name):
        return r'%%%%%%%%%%%%%%%%% FRAGMENT: {} %%%%%%%%%%%%%%%%%'.format(name)
