from reportcompiler.plugins.context_generators.context_generators \
    import FragmentContextGenerator


class StubContextGenerator(FragmentContextGenerator):
    """ Stub context generator. """
    name = 'stub'

    def generate_context(self, doc_var, data, metadata):
        return {'data': 'Stub context generated!!'}

__all__ = ['StubContextGenerator', ]
