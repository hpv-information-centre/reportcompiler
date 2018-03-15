""" errors.py

This module contains the errors for each stage of the fragment generation
process.

"""

__all__ = [
    'ContextGenerationError',
    'DataFetchingError',
    'MetadataRetrievalError',
    'PostProcessorError',
    'TemplateRendererException', ]


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
