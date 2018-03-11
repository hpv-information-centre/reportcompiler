""" rmarkdown.py

This module includes the template renderer using rmarkdown.

"""


import re
import jinja2
import os
import json
import shutil
from subprocess import run, PIPE, CalledProcessError
from jinja2.exceptions import UndefinedError
from reportcompiler.plugins.template_renderers.base \
    import TemplateRenderer


class RMarkdownRenderer(TemplateRenderer):
    """ Template renderer for RMarkdown. """
    # TODO: Testing
    name = 'rmarkdown'

    def render_template(self, doc_var, context):
        try:
            template_tmp_dir = os.path.join(
                                    context['meta']['tmp_path'],
                                    'templates')
            if not os.path.exists(template_tmp_dir):
                os.mkdir(template_tmp_dir)

            self._generate_temp_templates(doc_var, context)

            try:
                r_code = "library(knitr);" + \
                         "setwd('{}');".format(
                             context['meta']['tmp_path'].replace(
                                 '\\', '\\\\')) + \
                         "knitr::knit(input='{}', encoding='UTF-8');".format(
                            os.path.join(context['meta']['tmp_path'],
                                         'templates',
                                         context['meta']['main_template']).
                            replace('\\', '\\\\'))
                command = 'Rscript --vanilla -e "{}"'.format(
                                r_code.replace('"', '\\"'))
                run(command,
                    shell=True,
                    check=True,
                    stdout=PIPE,
                    stderr=PIPE,
                    universal_newlines=True)
            except CalledProcessError as e:
                TemplateRenderer.raise_rendering_exception(
                                    context,
                                    exception=e,
                                    message=e.stdout)

            shutil.rmtree(template_tmp_dir)

            return None
        except UndefinedError as e:
            TemplateRenderer.raise_rendering_exception(context, exception=e)

    def _generate_temp_templates(self, doc_var, context):
        context_info = context['meta']['template_context_info']
        for template_file, _ in context_info:
            with open(os.path.join(context['meta']['templates_path'],
                                   template_file), 'r') as f_orig, \
                 open(os.path.join(context['meta']['tmp_path'],
                                   'templates',
                                   template_file), 'w') as f_tmp:
                content = f_orig.read()
                if template_file == context['meta']['main_template']:
                    metadata, content = re.findall(
                                            pattern='[ ]*(---.*?---)(.*)',
                                            string=content,
                                            flags=re.DOTALL)[0]
                    header = """
                             ```{{r echo=FALSE, message=FALSE}}
                             library(jsonlite)
                             docvar = fromJSON('{}')
                             context = fromJSON('{}')
                             ```
                             """.format(json.dumps(doc_var),
                                        json.dumps(context).replace(
                                            '\\', '\\\\'))
                    content = '\n'.join([metadata, header, content])
                f_tmp.write(content)

    def included_templates(self, content):
        matches = re.findall(pattern='```{.*child[ ]*=[ ]*[\'"](.*?)[\'"]',
                             string=content)
        matches = [t.split(',') for t in matches]
        templates = []
        for m in matches:
            templates += [t.strip() for t in m]
        return templates

__all__ = ['RMarkdownRenderer', ]
