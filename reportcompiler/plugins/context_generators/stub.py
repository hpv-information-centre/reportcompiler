from reportcompiler.plugins.context_generators.base \
    import ContextGenerator


class StubContextGenerator(ContextGenerator):
    """ Stub context generator. """
    name = 'stub'

    def generate_context(self, doc_var, data, metadata):
        return {'data': 'Stub context generated!!'}

__all__ = ['StubContextGenerator', ]
