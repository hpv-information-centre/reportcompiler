import logging
from abc import abstractmethod
from reportcompiler.plugins.plugin_module import PluginModule
from reportcompiler.plugins.errors import TemplateRendererException


class TemplateRenderer(PluginModule):

    @abstractmethod
    def render_template(self, template_path, main_template, doc_var, context):
        raise NotImplementedError('Template rendering not implemented for {}'.format(self.__class__))

    @abstractmethod
    def included_templates(self, content):
        raise NotImplementedError('Included templates method not implemented for {}'.format(self.__class__))

    @classmethod
    def _get_default_handler(cls, extension):
        return TemplateRenderer.get('jinja')

    @classmethod
    def raise_rendering_exception(cls, exception, context, message=None):
        exception_info = message if message else str(exception)
        full_msg = 'Template rendering error\n\n{}'.format(exception_info)
        logger = logging.getLogger(context['meta']['logger'])
        logger.error('[{}] {}'.format(context['meta']['doc_suffix'], full_msg))
        err = TemplateRendererException(full_msg)
        if exception:
            err.with_traceback(exception.__traceback__)
        raise err from None
