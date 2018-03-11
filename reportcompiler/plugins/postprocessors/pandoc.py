""" pandoc.py

This module includes the postprocessor using pandoc.

"""


import os
from subprocess import run, PIPE, CalledProcessError
from jinja2.exceptions import UndefinedError
from reportcompiler.plugins.postprocessors.base import PostProcessor


class PandocPostProcessor(PostProcessor):
    """ Postprocessor for pandoc. """
    # TODO: Testing

    def postprocess(self, doc_var, doc, postprocessor_info, context):
        try:
            md_file = os.path.splitext(
                        os.path.join(
                            context['meta']['tmp_path'],
                            context['meta']['main_template']))[0] + '.md'
            suffix = context['meta']['doc_suffix']
            filename = context['meta']['name']
            if suffix != '':
                filename = filename + '-' + suffix

            try:
                pandoc_cmd = \
                    "\"C:/Program Files/RStudio/bin/pandoc/pandoc\" " + \
                    "+RTS -K512m -RTS " + \
                    "--standalone " + \
                    "\"{input_md}\" ".format(
                                input_md=md_file.replace('\\', '\\\\')) + \
                    self._get_pandoc_args() + " " + \
                    "--output \"{output_file}.{ext}\" ".format(
                        output_file=os.path.join(
                                context['meta']['out_path'],
                                filename).replace('\\', '\\\\'),
                        ext=self._get_output_extension())
                # TODO: Do something with the result
                run(pandoc_cmd,
                    shell=True,
                    check=True,
                    stdout=PIPE,
                    stderr=PIPE,
                    universal_newlines=True,
                    cwd=context['meta']['tmp_path'])
            except CalledProcessError as e:
                PostProcessor.raise_postprocessor_exception(
                                    context,
                                    exception=e,
                                    message=e.stdout)

            return None
        except UndefinedError as e:
            PostProcessor.raise_postprocessor_exception(context, exception=e)

    def _get_pandoc_args(self):
        return ' '.join(['--to latex', '--latex-engine pdflatex', ])

    def _get_output_extension(self):
        return 'pdf'


class PandocHTMLPostProcessor(PandocPostProcessor):
    """ Postprocessor for pandoc to HTML. """
    # TODO: Finish implementation

    def _get_pandoc_args(self):
        return ' '.join(['--to html', ])

    def _get_output_extension(self):
        return 'html'

__all__ = ['PandocPostprocessor', 'PandocHTMLPostprocessor', ]
