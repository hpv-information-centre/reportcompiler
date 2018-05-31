""" pdflatex.py

This module includes the postprocessor using pdflatex.

"""

import os
from subprocess import run, PIPE, CalledProcessError
from shutil import which
from reportcompiler.plugins.postprocessors.base import PostProcessor

__all__ = ['PdflatexPostProcessor', ]


class PdflatexPostProcessor(PostProcessor):
    """ Postprocessor for pdflatex. """

    def postprocess(self, doc_param, doc, postprocessor_info, context):
        suffix = context['meta']['doc_suffix']
        filename = context['meta']['doc_name']
        if suffix != '':
            filename = filename + '-' + suffix

        tmp_path = context['meta']['tmp_path']
        out_path = context['meta']['out_path']
        tex_file = os.path.join(tmp_path, filename + '.tex')

        try:
            if which('pdflatex') is None:
                PostProcessor.raise_postprocessor_exception(
                    context,
                    message='pdflatex not found in PATH. Please install it '
                            'or configure your PATH.')

            with open(tex_file, 'w') as f:
                f.write(doc)
            command = 'pdflatex -interaction=nonstopmode ' \
                      '-halt-on-error ' \
                      '-aux-directory="{}" ' \
                      '-output-directory="{}" ' \
                      '"{}"'.format(tmp_path,
                                    out_path,
                                    tex_file)
            run(command,
                shell=True,
                check=True,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True)
        except CalledProcessError as e:
            PostProcessor.raise_postprocessor_exception(
                context,
                exception=e,
                message=e.stdout)
