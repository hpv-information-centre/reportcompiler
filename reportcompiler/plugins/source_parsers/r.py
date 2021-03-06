""" r.py

This module includes the context generator using R.

"""

import json
from collections import OrderedDict
from subprocess import run, PIPE, CalledProcessError
from shutil import which
from reportcompiler.plugins.source_parsers.base \
    import SourceParser

__all__ = ['RParser', ]


class RParser(SourceParser):
    """ Context generator for R scripts. """

    def generate_context(self, doc_param, data, metadata):
        r_code = "library(jsonlite, quietly=TRUE);\
                    source('{}');\
                    cache_file <- fromJSON(file('{}'));\
                    doc_param <- cache_file[['doc_param']];\
                    data <- cache_file[['data']];\
                    metadata <- cache_file[['metadata']];\
                    print(toJSON(generate_context(doc_param, data, metadata),\
                        auto_unbox=TRUE))"

        r_code = r_code.format(metadata['fragment_path'].replace('\\', '\\\\'),
                               metadata['cache_file'].replace('\\', '\\\\')
                                                     .replace('\'', '\\\''))
        output = None
        try:
            if which('Rscript') is None:
                SourceParser.raise_generator_exception(
                    doc_param, data, context,
                    message='Rscript not found in PATH. Please install it '
                            'or configure your PATH.')

            command = 'Rscript --vanilla -e "{}"'.format(
                                                    r_code.replace('"', '\\"'))
            output = run(command,
                         shell=True,
                         check=True,
                         stdout=PIPE,
                         stderr=PIPE,
                         universal_newlines=True)
        except CalledProcessError as e:
            SourceParser.raise_generator_exception(
                doc_param,
                data,
                metadata,
                exception=e,
                message=e.stderr)
        return json.loads(output.stdout)

    def retrieve_fragment_metadata(self, doc_param, metadata):
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
                               json.dumps(doc_param),
                               json.dumps(metadata))
        output = None
        try:
            if which('Rscript') is None:
                SourceParser.raise_retriever_exception(
                    doc_param,
                    metadata,
                    message='Rscript not found in PATH. Please install it '
                            'or configure your PATH.')

            command = 'Rscript --vanilla -e "{}"'.format(r_code)
            output = run(command,
                         shell=True,
                         check=True,
                         stdout=PIPE,
                         stderr=PIPE,
                         universal_newlines=True)
        except CalledProcessError as e:
            SourceParser.raise_retriever_exception(
                doc_param,
                metadata,
                exception=e,
                message=e.stderr)
        return json.loads(output.stdout,
                          object_pairs_hook=OrderedDict)
