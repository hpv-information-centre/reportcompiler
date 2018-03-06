class ContextGenerationError(Exception):
    """ Exception on context generation """
    pass


class DataFetchingError(Exception):
    """ Exception on data fetching """
    pass


class MetadataRetrievalError(Exception):
    """ Exception on metadata retrieval """
    pass


class PostProcessorError(Exception):
    """ Exception on postprocessing """
    pass


class TemplateRendererException(Exception):
    """ Exception on template rendering """
    pass

__all__ = [
            'ContextGenerationError',
            'DataFetchingError',
            'MetadataRetrievalError',
            'PostProcessorError',
            'TemplateRendererException', ]
