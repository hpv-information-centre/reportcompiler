import re
import jinja2
from jinja2.exceptions import UndefinedError
import itertools
from reportcompiler.plugins.template_renderers.template_renderers import TemplateRenderer


class JinjaRenderer(TemplateRenderer):
    name = 'jinja'

    def render_template(self, template_path, main_template, doc_var, context):
        # TODO: StrictUndefined vs DebugUndefined
        try:
            environment = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path), undefined=jinja2.StrictUndefined)
            self._setup_environment(environment)
            # TODO: render vs generate
            return environment.get_template(context['meta']['main_template']).render(context)
        except UndefinedError as e:
            TemplateRenderer.raise_rendering_exception(e, context)

    def included_templates(self, content):
        templates = re.findall(pattern='.*{%.*%}.*', string=content)
        templates = [t for t in templates if len(re.findall(pattern='^[ ]*##.*', string=t)) == 0]
        templates = [re.findall(pattern='\{%[ ]*include[ ]*[\'"](.*?)[\'"][ ]*%\}',
                                        string=t) for t in templates]
        templates = list(itertools.chain.from_iterable(templates))
        return templates

    def _setup_environment(self, environment):
        pass # Default environment


class JinjaLatexRenderer(JinjaRenderer):
    name = 'jinja-latex'

    def _setup_environment(self, jinja_env):
        def escape_tex(value):
            LATEX_SUBS = (
                (re.compile(r'\\'), r'\\\\'),
                (re.compile(r'([{}_#%&$])'), r'\\\1'),
                (re.compile(r'~'), r'\~{}'),
                (re.compile(r'\^'), r'\^{}'),
                (re.compile(r'"'), r"''"),
                (re.compile(r'\.\.\.+'), r'\\ldots'),
                (re.compile(r'_'), r'\_'),
            )

            newval = value
            for pattern, replacement in LATEX_SUBS:
                newval = pattern.sub(replacement, newval)
            return newval

        def escape_path(value):
            return value.replace('\\', '/')

        jinja_env.block_start_string = '\BLOCK{'
        jinja_env.block_end_string = '}'
        jinja_env.variable_start_string = '\VAR{'
        jinja_env.variable_end_string = '}'
        jinja_env.comment_start_string = '\COMMENT{'
        jinja_env.comment_end_string = '}'
        jinja_env.line_comment_preffix = '%#'
        jinja_env.filters['escape_tex'] = escape_tex
        jinja_env.filters['escape_path'] = escape_path
        jinja_env.trim_blocks = True
        jinja_env.autoescape = False

    def included_templates(self, content):
        templates = re.findall(pattern='.*BLOCK.*', string=content)
        templates = [t for t in templates if len(re.findall(pattern='^[ ]*%#.*', string=t)) == 0]
        templates = [re.findall(pattern='\\BLOCK\{[ ]*include[ ]*[\'"](.*?)[\'"][ ]*\}',
                                        string=t) for t in templates]
        templates = list(itertools.chain.from_iterable(templates))
        return templates
