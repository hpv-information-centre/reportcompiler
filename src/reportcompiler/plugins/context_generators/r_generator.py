import json
from subprocess import run, PIPE, CalledProcessError
from reportcompiler.plugins.context_generators.context_generators \
    import FragmentContextGenerator


class RContextGenerator(FragmentContextGenerator):
    """ Context generator for R scripts. """
    name = 'r'

    def generate_context(self, doc_var, data, metadata):
        r_code = "library(jsonlite, quietly=TRUE);\
                    source('{}');\
                    doc_var <- fromJSON(file('{}'));\
                    data <- fromJSON(file('{}'));\
                    metadata <- fromJSON(file('{}'));\
                    print(toJSON(generate_context(doc_var, data, metadata),\
                        auto_unbox=TRUE))"

        r_code = r_code.format(metadata['fragment_path'].replace('\\', '\\\\'),
                               metadata['docvar_file'].replace('\\', '\\\\'),
                               metadata['data_file'].replace('\\', '\\\\'),
                               metadata['metadata_file'].replace('\\', '\\\\'))
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
            FragmentContextGenerator.raise_generator_exception(
                metadata['fragment_path'],
                e,
                metadata,
                message=e.stderr)
        return json.loads(output.stdout)

__all__ = ['RContextGenerator', ]