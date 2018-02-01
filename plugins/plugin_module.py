import importlib
import os
import re
import inspect
from abc import ABCMeta


class PluginModule(metaclass=ABCMeta):

    @classmethod
    def _get_default_handler(cls, extension):
        raise NotImplementedError('No default handlers are available for {}'.format(cls))

    @classmethod
    def get(cls, id=None, extension=None):
        class_dict = cls._get_classes()
        if id:
            try:
                if isinstance(id, dict): # It might be a dictionary with more info, we get the type from within
                    id = id['type']
                return class_dict[id]()
            except KeyError:
                raise NotImplementedError('{} "{}" does not exist'.format(cls.__name__, id))
        else:
            try:
                return cls._get_default_handler(extension=extension.lower())
            except NotImplementedError:
                raise NotImplementedError('There is no default {} for extension .{}'.format(cls.__name__, id))

    @classmethod
    def _get_classes(cls):
        modules = cls._get_modules()
        classes = set()
        def is_data_fetcher(other_cls):
            return inspect.isclass(other_cls) and issubclass(other_cls, cls)
        for module in modules:
            module_classes = [cls for name, cls in inspect.getmembers(module, is_data_fetcher)]
            classes = classes.union(module_classes) # Only adding the class itself
        classes.remove(cls)
        class_dict = {}
        # fetchers = FragmentDataFetcher._get_all_subclasses(FragmentDataFetcher)
        for current_class in classes:
            try:
                if class_dict.get(current_class.name) is not None:
                    raise NameError('Name conflict ("{}") with classes {} and {}'.format(current_class.name, class_dict[current_class.name], current_class))
                class_dict[current_class.name] = current_class
            except AttributeError:
                raise AttributeError('Class "{}" has no "name" attribute'.format(current_class))
        return class_dict

    @classmethod
    def _get_modules(cls):
        pysearchre = re.compile('.py$', re.IGNORECASE)
        pluginfiles = filter(pysearchre.search, os.listdir(os.path.dirname(inspect.getfile(cls))))
        form_module = lambda fp: '.' + os.path.splitext(fp)[0]
        plugins = map(form_module, pluginfiles)
        # import parent module / namespace
        importlib.import_module(cls.__module__)
        modules = []
        for plugin in plugins:
            if not plugin.startswith('__'):
                modules.append(importlib.import_module(plugin, package=PluginModule._get_module_package(cls.__module__)))

        return modules

    @staticmethod
    def _get_module_package(module):
        return '.'.join(module.split('.')[:-1])

    @classmethod
    def _get_all_subclasses(cls):
        all_subclasses = []

        # for subclass in target_cls.__subclasses__():
        # 	all_subclasses.append(subclass)
        # 	all_subclasses.extend(cls._get_all_subclasses(subclass))
        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(cls._get_all_subclasses(subclass))

        return all_subclasses
