import importlib
import os
import re
import inspect
from abc import ABCMeta


class PluginModuleMeta(type):
    """ Base metaclass to make subclasses inherit docstrings from their
    parents if empty. """
    # TODO: Check efficiency
    def __new__(mcls, classname, bases, cls_dict):
        cls = super().__new__(mcls, classname, bases, cls_dict)
        for name, member in cls_dict.items():
            if (not getattr(member, '__doc__') and
                    hasattr(bases[-1], name) and
                    hasattr(getattr(bases[-1], name), '__doc__')):
                member.__doc__ = getattr(bases[-1], name).__doc__
        return cls


class PluginModule(object, metaclass=PluginModuleMeta):
    """ Base class that implements the plugin architecture. All direct
    subclasses of this module represent different stages and they have a
    factory method that scans their directory (e.g. context_generators,
    data_fetchers, ...) and instantiates a particular subsubclass (e.g.
    PythonContextGenerator) with only their name (e.g. 'python'). For new
    plugins of a particular type this doesn't require any imports; this
    class automatically scans the directory for suitable modules and
    classes."""

    @classmethod
    def _get_default_handler(cls, **kwargs):
        """
        In case no explicit plugin is specified, each plugin type can specify
        a default plugin.
        :param dict kwargs: Parameters to decide on a default
        :returns: Default plugin
        :rtype: PluginModule
        """
        raise NotImplementedError(
            'No default handlers are available for {}'.format(cls))

    @classmethod
    def get(cls, id=None, **kwargs):
        """
        Instantiates the specified plugin
        :param str id: plugin id (e.g. 'mysql', 'python', ...)
        :param dict kwargs: optional arguments
        :returns: Plugin
        :rtype: PluginModule
        """
        class_dict = cls._get_classes()
        if id:
            try:
                # It might be a dictionary with more info, we get the type
                # from within
                if isinstance(id, dict):
                    id = id['type']
                return class_dict[id]()
            except KeyError:
                raise NotImplementedError(
                    '{} "{}" does not exist'.format(cls.__name__, id))
        else:
            try:
                return cls._get_default_handler(**kwargs)
            except NotImplementedError:
                raise NotImplementedError(
                    'There is no default {} for extension .{}'.format(
                        cls.__name__, id))

    @classmethod
    def _get_classes(cls):
        """
        Scans the corresponding directory and returns information about
        suitable subclasses.
        :return: Dictionary with the class names as keys and the classes
        themselves as values
        """
        modules = cls._get_modules()
        classes = set()

        def is_plugin_subclass(other_cls):
            return inspect.isclass(other_cls) and issubclass(other_cls, cls)

        for module in modules:
            module_classes = [cls
                              for name, cls
                              in inspect.getmembers(module,
                                                    is_plugin_subclass)]
            classes = classes.union(module_classes)
        classes.remove(cls)
        class_dict = {}
        # fetchers = FragmentDataFetcher.
        #   _get_all_subclasses(FragmentDataFetcher)
        for current_class in classes:
            try:
                if class_dict.get(current_class.name) is not None:
                    raise NameError(
                        'Name conflict ("{}") with classes {} and {}'.
                        format(current_class.name,
                               class_dict[current_class.name], current_class))
                class_dict[current_class.name] = current_class
            except AttributeError:
                raise AttributeError(
                    'Class "{}" has no "name" attribute'.format(current_class))
        return class_dict

    @classmethod
    def _get_modules(cls):
        """
        Scans the corresponding directory (e.g. context_generators) and
        returns information about suitable modules.
        :return: List of all module objects in the directory
        """
        def get_module_package(module):
            """ Returns the package containing the module with the name
            specified """
            return '.'.join(module.split('.')[:-1])

        pysearchre = re.compile('.py$', re.IGNORECASE)
        pluginfiles = filter(pysearchre.search,
                             os.listdir(os.path.dirname(
                                            inspect.getfile(cls))))

        def form_module(fp):
            return '.' + os.path.splitext(fp)[0]

        plugins = map(form_module, pluginfiles)
        # import parent module / namespace
        importlib.import_module(cls.__module__)
        modules = []
        for plugin in plugins:
            if not plugin.startswith('__'):
                try:
                    modules.append(importlib.import_module(
                                plugin,
                                package=get_module_package(cls.__module__)))
                except ImportError as e:
                    if not getattr(cls, '_import_errors_printed', False):
                        print("Warning: '{}' module not available "
                              ": {}".format(plugin[1:], e))
                    cls._import_errors_printed = True

        return modules

    @classmethod
    def _get_all_subclasses(cls):
        """ Returns all subclasses of the current class """
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(cls._get_all_subclasses(**subclass))

        return all_subclasses

__all__ = ['PluginModule', ]
