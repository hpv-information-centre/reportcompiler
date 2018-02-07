import json
from subprocess import run, PIPE, CalledProcessError
from reportcompiler.plugins.metadata_retriever.metadata_retriever import FragmentMetadataRetriever


class RMetadataRetriever(FragmentMetadataRetriever):
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
            output = run(command, shell=True, check=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        except CalledProcessError as e:
            FragmentMetadataRetriever.raise_retriever_exception(
                metadata['fragment_path'],
                e,
                metadata,
                message=e.stderr)
        return json.loads(output.stdout)
