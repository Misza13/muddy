import importlib

from pubsub import pub


class MuddyPlugin(object):
    configuration = {}
    
    def set_configuration(self, config):
        self.configuration = config
    
    def invoke_method(self, component_name, method_name, **kwargs):
        pub.sendMessage(component_name + '.' + method_name, **kwargs)


def IncomingTextHandler(func):
    return flag_as_handler(func, 'IncomingTextHandler')


def flag_as_handler(func, handler_name):
    if not hasattr(func, 'muddy_plugin_flags'):
        func.muddy_plugin_handler = []

    func.muddy_plugin_handler.append(handler_name)

    return func


class PluginManager:
    def __init__(self):
        self.plugins = []
        self.handlers = {
            'IncomingTextHandler': []
        }
    
    def load_from_config(self, config):
        for plugin_def in config['plugins']:
            module_name = plugin_def['module']
            class_name = plugin_def['class']
            
            module = importlib.import_module(module_name)
            for thing in dir(module):
                if thing == class_name:
                    plugin_class = getattr(module, class_name)
                    plugin = plugin_class()
                    if 'configuration' in plugin_def:
                        plugin.set_configuration(plugin_def['configuration'])
                    
                    self.register_plugin(plugin)
    
    def register_plugin(self, plugin):
        # TODO: Duplicate/de-/re-registration
        self.plugins.append(plugin)
        
        for attr in dir(plugin):
            method = getattr(plugin, attr)
            if hasattr(method, 'muddy_plugin_handler'):
                for handler_name in method.muddy_plugin_handler:
                    self.handlers[handler_name].append(method)
    
    def get_handlers(self, handler_name):
        return self.handlers[handler_name]
