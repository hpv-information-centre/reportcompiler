import os
from subprocess import run, PIPE, DEVNULL, CalledProcessError
from reportcompiler.plugins.postprocessors.postprocessors import PostProcessor


class PdflatexPostProcessor(PostProcessor):
    name = 'pdflatex'

    def postprocess(self, doc_var, doc, report_path, postprocessor_info, context):
        suffix = context['meta']['doc_suffix']
        filename = context['meta']['name'] if suffix == '' else context['meta']['name'] + '-' + suffix

        tmp_path = context['meta']['tmp_path']
        out_path = context['meta']['out_path']
        tex_file = os.path.join(tmp_path, filename + '.tex')

        try:
            with open(tex_file, 'w') as f:
                f.write(doc)
            command = 'pdflatex -interaction=nonstopmode -halt-on-error {} -aux-directory={} -output-directory={}'.format(tex_file, tmp_path, out_path)
            run(command, shell=True, check=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        except CalledProcessError as e:
            PostProcessor.raise_postprocessor_exception(e, context, message=e.stdout)
