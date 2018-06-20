from reportcompiler.documents import DocumentSpecification
from reportcompiler.errors import DocumentGenerationError


def compile_report():
    import sys
    import json

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
    print('All documents generated successfully!')
