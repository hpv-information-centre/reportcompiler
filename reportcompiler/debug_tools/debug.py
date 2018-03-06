import json
import os
import sys
import pandas as pd
from reportcompiler.plugins.context_generators.python_generator \
    import PythonContextGenerator
from reportcompiler.plugins.context_generators.context_generators \
    import FragmentContextGenerator


def compile_last_fragment(report_path):
    with open(os.path.join(report_path,
                           '_meta',
                           'last_debug_errors'), 'r') as f:
        last_values = json.load(f)

    for frag in last_values:
        doc_var = frag['doc_var']
        data = {name: pd.DataFrame(data)
                for name, data in frag['data'].items()}
        metadata = frag['metadata']

        fragment = os.path.basename(metadata['fragment_path'])
        _, ext = os.path.splitext(fragment)

        generator_info = metadata.get('context_generator')
        generator = FragmentContextGenerator.get(id=generator_info,
                                                 extension=ext)
        if isinstance(generator_info, str):
            generator = FragmentContextGenerator.get(id=generator_info,
                                                     extension=ext)
        elif isinstance(generator_info, dict):
            generator = FragmentContextGenerator.get(
                            id=generator_info[ext])

        if generator.__class__ == PythonContextGenerator:
            sys.path.append(os.path.join(report_path, frag['report'], 'src'))
            try:
                ctx = PythonContextGenerator().generate_context(doc_var,
                                                                data,
                                                                metadata)
                print('\n{}\n'.format(ctx))
                print('*** {} has finished successfully.'.format(fragment))
            except Exception:
                print('*** {} has finished with errors.'.format(fragment))
        else:
            print("*** {} doesn't use python, skipping...".format(fragment))


if __name__ == '__main__':
    compile_last_fragment(report_path=os.environ['REPORTS_PATH'])
