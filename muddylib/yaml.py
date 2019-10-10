import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader as Loader


def load(data):
    return yaml.load(data, Loader=Loader)
