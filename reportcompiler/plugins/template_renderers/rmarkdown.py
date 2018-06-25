""" rmarkdown.py

This module includes the template renderer using rmarkdown.

"""

import re
import os
import json
import shutil
import anytree
from subprocess import run, PIPE, CalledProcessError
from jinja2.exceptions import UndefinedError
from reportcompiler.plugins.template_renderers.base \
    import TemplateRenderer

__all__ = ['RMarkdownRenderer', ]


class RMarkdownRenderer(TemplateRenderer):
    """ Template renderer for RMarkdown. """
    # TODO: Testing

    def _comment_disabled_templates(self,
                                    fragment_content,
                                    all_included_templates):
        child_template_info = self.included_templates(
                                            fragment_content)
        for child_name, child_block in child_template_info:
            if child_name not in all_included_templates:
                fragment_content = fragment_content.replace(
                    child_block,
                    '{} {} {}'.format("<!-- ",
                                      child_block,
                                      " -->")
                )
        return fragment_content

    def render_template(self, doc_param, template_tree, context):
        try:
            if shutil.which('Rscript') is None:
                TemplateRenderer.raise_rendering_exception(
                    context,
                    message='Rscript not found in PATH. Please install it '
                            'or configure your PATH.')

            template_tmp_dir = os.path.join(
                context['meta']['tmp_path'],
                'templates')
            if not os.path.exists(template_tmp_dir):
                os.mkdir(template_tmp_dir)

            self._generate_temp_templates(doc_param, template_tree, context)

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

    def _generate_temp_templates(self, doc_param, template_tree, context):
        all_included_templates = anytree.findall(template_tree.node,
                                                 lambda _: True)
        all_included_templates = [n.name for n in all_included_templates]

        for subtree in anytree.PreOrderIter(template_tree.node):
            node = subtree
            template_file = node.name
            template_path = '.'.join([os.path.splitext(n.name)[0]
                                      for n in node.path[1:]])
            with open(os.path.join(context['meta']['templates_path'],
                                   template_file), 'r') as f_orig, \
                    open(os.path.join(context['meta']['tmp_path'],
                                      'templates',
                                      template_file), 'w') as f_tmp:
                content = f_orig.read()
                content = self._comment_disabled_templates(
                    content, all_included_templates)

                if template_file == context['meta']['main_template']:
                    metadata, content = re.findall(
                                            pattern='[ ]*(---.*?---)(.*)',
                                            string=content,
                                            flags=re.DOTALL)[0]

                    header = """
                             ```{{r echo=FALSE, message=FALSE}}
                             library(jsonlite)
                             docparam = fromJSON('{}')
                             context = fromJSON('{}')
                             ```
                             """.format(json.dumps(doc_param),
                                        json.dumps(context).replace(
                                            '\\', '\\\\'))
                    content = '\n'.join([metadata, header, content])
                f_tmp.write(content)

    def included_templates(self, content):
        matches = re.findall(pattern='```{.*child[ ]*=[ ]*[\'"](.*?)[\'"]',
                             string=content)
        matches = [t.split(',') for t in matches]
        template_names = []
        for m in matches:
            template_names += [t.strip() for t in m]

        template_blocks = re.findall(
                        pattern='```{.{0,20}child[ ]*=[ ]*[\'"].*?[\'"].*?```',
                        string=content,
                        flags=re.DOTALL)

        return list(zip(template_names, template_blocks))

    def get_fragment_start_comment(self, name):
        return r'<!-- %%%%%%%%%%%% FRAGMENT: {} %%%%%%%%%%%% -->'.format(name)
