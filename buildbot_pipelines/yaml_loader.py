import yaml
from buildbot.plugins import util
from buildbot.plugins.db import get_plugins

from . import package_loader

steps = get_plugins('steps', None, load_now=True)


class PipeLineYamlLoader(yaml.SafeLoader):

    def construct_object(self, node, deep=False):
        if node.tag not in self.yaml_constructors:
            if not node.tag.startswith("!"):
                raise AttributeError("illegal yaml tag: {}".format(node.tag.encode('utf-8')))
            k = node.tag[1:]
            if k in steps.names:
                v = steps.get(k)
                self.add_constructor(k, lambda node: self.construct_custom_object(v, node))
            else:
                raise AttributeError("No buildbot plugin found for name: {}".format(k))
        return yaml.SafeLoader.construct_object(self, node, deep)

    def construct_import(self, node):
        imports = self.construct_sequence(node)

        def makeConstructor(typ):
            def constructor(loader, node):
                return loader.construct_custom_object(typ, node)
            return constructor
        for i in imports:
            for k, v in package_loader.import_package(i).items():
                self.add_constructor(k, makeConstructor(v))

    def construct_custom_object(self, loader, node):
        args = []
        kwargs = {}
        if isinstance(node, yaml.nodes.ScalarNode):
            scalar = self.construct_scalar(node)
            if scalar == "":
                args = []
            else:
                args = [scalar]
        elif isinstance(node, yaml.nodes.SequenceNode):
            args = yaml.constructor.BaseConstructor.construct_sequence(node, deep=True)
        elif isinstance(node, yaml.nodes.MappingNode):
            kwargs = yaml.constructor.BaseConstructor.construct_mapping(self, node, deep=True)
        r = loader(*args, **kwargs)
        return r

    def construct_interpolate(self, node):
        value = self.construct_scalar(node)
        print(value)
        return util.Interpolate(value)


PipeLineYamlLoader.add_constructor("!Imports", PipeLineYamlLoader.construct_import)
PipeLineYamlLoader.add_constructor(u'!Interpolate', PipeLineYamlLoader.construct_interpolate)
PipeLineYamlLoader.add_constructor(u'!i', PipeLineYamlLoader.construct_interpolate)


class PipelineYml(object):
    def __init__(self, yaml_text):
        self.cfg = yaml.load(yaml_text, Loader=PipeLineYamlLoader)
