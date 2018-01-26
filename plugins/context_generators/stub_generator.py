from reportcompiler.plugins.context_generators.context_generators import FragmentContextGenerator


class StubContextGenerator(FragmentContextGenerator):
    name = 'stub'

    def generate_context(self, doc_var, data, metadata):
        return {'data': 'Stub context generated!!'}
