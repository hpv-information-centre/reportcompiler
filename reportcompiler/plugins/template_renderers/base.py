""" base.py

This module includes the base plugin interface for template renderers.

"""


import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import TemplateRendererException


class TemplateRenderer(PluginModule):
    """ Plugin that implements the template rendering stage for the document (see
    architecture). """

    entry_point_group = 'template_renderers'

    @abstractmethod
    def render_template(self, doc_var, context):
        """ Renders the template after the context is generated for all fragments.

        :param OrderedDict doc_var: Document variable
        :param dict context: Context dictionary with keys 'data' (context
            generated from fragments) and 'meta' (report metadata)
        """
        raise NotImplementedError(
            'Template rendering not implemented for {}'.format(self.__class__))

    @abstractmethod
    def included_templates(self, content):
        """ Returns the included templates in the specified content.

        :param str content: Template content
        :returns: List of included templates
        :rtype: list
        """
        raise NotImplementedError(
            'Included templates method not implemented for {}'.format(
                self.__class__))

    @classmethod
    def _get_default_handler(cls, **kwargs):
        return TemplateRenderer.get('jinja')

    @classmethod
    def raise_rendering_exception(cls, context, exception=None, message=None):
        """
        Returns a template rendering exception with the necessary info
        attached.

        :param dict context: Context for fragment
        :param Exception exception: Exception returned by template rendering
        :param str message: Optional message for exception
        """
        exception_info = message if message else str(exception)
        full_msg = 'Template rendering error\n\n{}'.format(exception_info)
        if context['meta'].get('logger_name'):
            logger = logging.getLogger(context['meta']['logger_name'])
            logger.error('[{}] {}'.format(context['meta']['doc_suffix'],
                                          full_msg))
        err = TemplateRendererException(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None

__all__ = ['TemplateRenderer', ]
