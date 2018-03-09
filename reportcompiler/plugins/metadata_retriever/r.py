import json
from subprocess import run, PIPE, CalledProcessError
from reportcompiler.plugins.metadata_retriever.base \
    import MetadataRetriever


class RMetadataRetriever(MetadataRetriever):
    """ Metadata retriever for R scripts. """
    name = 'r'

    def retrieve_fragment_metadata(self, doc_var, metadata):
        r_code = "library(jsonlite, quietly=TRUE);\
                    source('{}');\
                    all.var.names <- ls();\
                    var.list <- list();\
                    for(name in all.var.names) {{\
                        if (typeof(get(name)) != 'closure')\
                            var.list[name] <- list(get(name));\
                    }};\
                    print(toJSON(var.list, auto_unbox=TRUE))"
        r_code = r_code.format(metadata['fragment_path'].replace('\\', '\\\\'),
                               json.dumps(doc_var),
                               json.dumps(metadata))
        output = None
        try:
            # TODO: Check for Rscript first
            command = 'Rscript --vanilla -e "{}"'.format(r_code)
            output = run(command,
                         shell=True,
                         check=True,
                         stdout=PIPE,
                         stderr=PIPE,
                         universal_newlines=True)
        except CalledProcessError as e:
            MetadataRetriever.raise_retriever_exception(
                metadata,
                exception=e,
                message=e.stderr)
        return json.loads(output.stdout,
                          object_pairs_hook=collections.OrderedDict)

__all__ = ['RMetadataRetriever', ]
