""" pandoc.py

This module includes the postprocessor using pandoc.

"""

import os
from subprocess import run, PIPE, CalledProcessError
from jinja2.exceptions import UndefinedError
from reportcompiler.plugins.postprocessors.base import PostProcessor

__all__ = ['PandocPostProcessor', 'PandocHTMLPostProcessor', ]


class PandocPostProcessor(PostProcessor):
    """ Postprocessor for pandoc. """
    # TODO: Testing and finish implementation

    def postprocess(self, doc_param, doc_path, postprocessor_info, context):
        try:
            md_file = os.path.join(
                        context['meta']['tmp_path'],
                        doc_path)
            suffix = context['meta']['doc_suffix']
            filename = context['meta']['doc_name']
            if suffix != '':
                filename += '-' + suffix

            if context['meta'].get('partial_generation_fragments'):
                filename += '__' + '-'.join(
                    context['meta']['partial_generation_fragments'])

            try:
                pandoc_cmd = \
                    "\"pandoc\" " + \
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
