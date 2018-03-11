""" r.py

This module includes the context generator using R.

"""


import json
from subprocess import run, PIPE, CalledProcessError
from reportcompiler.plugins.context_generators.base \
    import ContextGenerator


class RContextGenerator(ContextGenerator):
    """ Context generator for R scripts. """
    name = 'r'

    def generate_context(self, doc_var, data, metadata):
        r_code = "library(jsonlite, quietly=TRUE);\
                    source('{}');\
                    cache_file <- fromJSON(file('{}'));\
                    doc_var <- cache_file$doc_var;\
                    data <- cache_file$data;\
                    metadata <- cache_file$metadata;\
                    print(toJSON(generate_context(doc_var, data, metadata),\
                        auto_unbox=TRUE))"

        r_code = r_code.format(metadata['fragment_path'].replace('\\', '\\\\'),
                               metadata['cache_file'].replace('\\', '\\\\'))
        output = None
        try:
            command = 'Rscript --vanilla -e "{}"'.format(
                                                    r_code.replace('"', '\\"'))
            output = run(command,
                         shell=True,
                         check=True,
                         stdout=PIPE,
                         stderr=PIPE,
                         universal_newlines=True)
        except CalledProcessError as e:
            ContextGenerator.raise_generator_exception(
                metadata,
                exception=e,
                message=e.stderr)
        return json.loads(output.stdout)

__all__ = ['RContextGenerator', ]
