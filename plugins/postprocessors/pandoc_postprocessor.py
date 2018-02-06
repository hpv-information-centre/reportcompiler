import os
from subprocess import run, PIPE, CalledProcessError
from jinja2.exceptions import UndefinedError
from reportcompiler.plugins.postprocessors.postprocessors import PostProcessor


class PandocPostprocessor(PostProcessor):
    name = 'pandoc-pdf'

    def postprocess(self, doc_var, doc, postprocessor_info, context):
        try:
            md_file = os.path.splitext(os.path.join(context['meta']['tmp_path'], context['meta']['main_template']))[0] + '.md'
            suffix = context['meta']['doc_suffix']
            filename = context['meta']['name'] if suffix == '' else context['meta']['name'] + '-' + suffix

            try:
                pandoc_cmd = "\"C:/Program Files/RStudio/bin/pandoc/pandoc\" " + \
                "+RTS -K512m -RTS " + \
                "--standalone " + \
                "\"{input_md}\" ".format(input_md=md_file.replace('\\', '\\\\')) + \
                self._get_pandoc_args() + " " + \
                "--output \"{output_file}.{ext}\" ".format(output_file=os.path.join(context['meta']['out_path'], filename).replace('\\', '\\\\'),
                                                           ext=self._get_output_extension())
                # "--smart --self-contained "
                result = run(pandoc_cmd, shell=True, check=True, stdout=PIPE, stderr=PIPE, universal_newlines=True, cwd=context['meta']['tmp_path'])
            except CalledProcessError as e:
                PostProcessor.raise_postprocessor_exception(e, context, message=e.stdout)

            return None
        except UndefinedError as e:
            PostProcessor.raise_postprocessor_exception(e, context)

    def _get_pandoc_args(self):
        return ' '.join(['--to latex', '--latex-engine pdflatex', ])

    def _get_output_extension(self):
        return 'pdf'

class PandocHTMLPostprocessor(PandocPostprocessor):
    name = 'pandoc-html'
    # TODO: Implement

    def _get_pandoc_args(self):
        return ' '.join(['--to html', ])

    def _get_output_extension(self):
        return 'html'