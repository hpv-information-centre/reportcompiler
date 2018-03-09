import re
import jinja2
import os
import itertools
import shutil
from jinja2.exceptions import UndefinedError
from reportcompiler.plugins.template_renderers.base \
    import TemplateRenderer


class JinjaRenderer(TemplateRenderer):
    """ Template renderer for jinja2. """
    name = 'jinja'

    def render_template(self, doc_var, context):
        try:
            template_tmp_dir = os.path.join(
                                context['meta']['tmp_path'],
                                'templates')
            if not os.path.exists(template_tmp_dir):
                os.mkdir(template_tmp_dir)

            environment = jinja2.Environment(
                            loader=jinja2.FileSystemLoader(template_tmp_dir),
                            undefined=jinja2.StrictUndefined)
            self._setup_environment(environment)
            self._generate_temp_templates(environment, context)
            # TODO: render vs generate
            rendered_template = \
                environment.get_template(
                                context['meta']['main_template']).render(
                                                                    context)

            shutil.rmtree(template_tmp_dir, ignore_errors=True)

            return rendered_template
        except UndefinedError as e:
            TemplateRenderer.raise_rendering_exception(context, exception=e)

    def _generate_temp_templates(self, env, context):
        context_info = context['meta']['template_context_info']
        for template_file, dict_path in context_info:
            with open(os.path.join(context['meta']['templates_path'],
                                   template_file), 'r') as f_orig, \
                 open(os.path.join(context['meta']['tmp_path'],
                                   'templates',
                                   template_file), 'w') as f_tmp:
                content = f_orig.read()
                header = env.block_start_string + \
                    'with ctx = {}'.format(
                        'data.' + dict_path if dict_path != '' else 'data') + \
                    env.block_end_string + '\n'
                footer = '\n' + \
                         env.block_start_string + \
                         'endwith' + \
                         env.block_end_string
                f_tmp.write(header + content + footer)

    def included_templates(self, content):
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

    def _setup_environment(self, environment):
        pass  # Default environment


class JinjaLatexRenderer(JinjaRenderer):
    """ Template renderer for jinja2, with latex-friendly syntax. """
    name = 'jinja-latex'

    def _setup_environment(self, jinja_env):
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
        jinja_env.block_end_string = '}'
        jinja_env.variable_start_string = r'\VAR{'
        jinja_env.variable_end_string = '}'
        jinja_env.comment_start_string = r'\COMMENT{'
        jinja_env.comment_end_string = '}'
        jinja_env.line_comment_preffix = '%#'
        jinja_env.filters['escape_tex'] = escape_tex
        jinja_env.filters['escape_path'] = escape_path
        jinja_env.trim_blocks = True
        jinja_env.autoescape = False

    def included_templates(self, content):
        templates = re.findall(pattern='.*BLOCK.*', string=content)
        templates = [t
                     for t
                     in templates if len(re.findall(
                                            pattern='^[ ]*%#', string=t)) == 0]
        templates = [re.findall(
                pattern=r'\\BLOCK\{[ ]*include[ ]*[\'"](.*?)[\'"][ ]*\}',
                string=t) for t in templates]
        templates = list(itertools.chain.from_iterable(templates))
        return templates

__all__ = ['JinjaRenderer', 'JinjaLatexRenderer', ]
