import os
import sys
import json

from reportcompiler.documents import DocumentSpecification
from reportcompiler.errors import DocumentGenerationError


def compile_report():
    if len(sys.argv) < 3:
        print('Error: This command requires the path to the document '
              'specification followed by the document parameters to generate.')
        return

    docspec_path = sys.argv[1]
    docspec = DocumentSpecification(docspec_path)
    docparams = []
    for arg in sys.argv[2:]:
        try:
            docparam = json.loads(arg)
        except json.JSONDecodeError:
            docparam = arg  # Assuming simple value
        docparams.append(docparam)

    try:
        docspec.generate(docparams)
    except DocumentGenerationError as e:
        print(e)
        os._exit(1)
    print('All documents generated successfully!')
    os._exit(0)


def compile_fragment():
    if len(sys.argv) < 4:
        print('Error: This command requires the path to the document '
              'specification followed by the fragments name and the document '
              'parameters to generate.')
        return

    docspec_path = sys.argv[1]
    docspec = DocumentSpecification(docspec_path)

    try:
        separator_index = sys.argv.index('--')
        _fragments = sys.argv[2:separator_index]
        _docparams = sys.argv[separator_index+1:]
    except ValueError:
        _fragments = sys.argv[2]
        _docparams = sys.argv[3:]

    docparams = []
    for arg in _docparams:
        try:
            docparam = json.loads(arg)
        except json.JSONDecodeError:
            docparam = arg  # Assuming simple value
        docparams.append(docparam)

    try:
        docspec.generate(docparams, fragments=_fragments)
    except DocumentGenerationError as e:
        print(e)
        os._exit(1)
    print('All documents generated successfully!')
    os._exit(0)
