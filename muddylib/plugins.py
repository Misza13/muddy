from pubsub import pub


class MuddyPlugin(object):
    def invoke_method(self, component_name, method_name, **kwargs):
        pub.sendMessage(component_name + '.' + method_name, **kwargs)


def IncomingTextHandler(func):
    set_func_flag(func, 'IncomingTextHandler')

    return func


def set_func_flag(func, flag, value=True):
    if not hasattr(func, 'muddy_plugin_flags'):
        func.muddy_plugin_flags = {}

    func.muddy_plugin_flags[flag] = value

    return func