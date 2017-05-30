import re

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
        return util.Interpolate(value)


PipeLineYamlLoader.add_constructor("!Imports", PipeLineYamlLoader.construct_import)
PipeLineYamlLoader.add_constructor(u'!Interpolate', PipeLineYamlLoader.construct_interpolate)
PipeLineYamlLoader.add_constructor(u'!i', PipeLineYamlLoader.construct_interpolate)


class PipelineYml(object):
    def __init__(self, yaml_text):
        # warning: this may do networking + whl uncompressing to load the imports
        # need to process this on a thread when inside twisted/buildbot
        self.yaml_text = yaml_text
        self.cfg = yaml.load(yaml_text, Loader=PipeLineYamlLoader)

    @staticmethod
    def compute_matrix(matrix, matrix_include=None, matrix_exclude=None):
        matrix_list = []
        for k, vs in matrix.items():
            if matrix_list:
                next_matrix_list = []
                for matrix_item in matrix_list:
                    for v in vs:
                        _matrix_item = matrix_item.copy()
                        _matrix_item[k] = v
                        next_matrix_list.append(_matrix_item)
                matrix_list = next_matrix_list
            else:
                matrix_list = [{k: v} for v in vs]

        # manage matrix include: include, but only if it is not already there
        if matrix_include:
            # dict is not hashable, so we cannot implement uniqueness via list(set())
            # we first remove exact dupes, and then insert
            for include_item in matrix_include:
                matrix_list = [item for item in matrix_list if item != include_item]
            matrix_list.extend(matrix_include)
        excluded_items = []

        # manage matrix exclude
        if matrix_exclude:
            for exclude_items in matrix_exclude:
                for item in matrix_list:
                    # exclude works if all of exclude items keys are inside an item remove them.
                    # all item keys do not need to be in exclude item
                    for k, v in exclude_items.items():
                        if k not in item or item[k] != v:
                            break
                    else:
                        excluded_items.append(item)
        if excluded_items:
            matrix_list = [item for item in matrix_list if item not in excluded_items]
        return matrix_list

    def find_stages_for_branch(self, branch):
        for branch_re, stages in self.cfg.get('branches', {}).items():
            if re.match(branch_re, branch):
                return stages
        return []

    def generate_triggers(self, branch, event_category="push"):
        stages = self.find_stages_for_branch(branch)
        if isinstance(stages, dict):
            stages = stages.get(event_category, [])
        ret = []
        for stage_name in stages:
            stage = self.cfg.get('stages', {}).get(stage_name, {})
            matrix = self.compute_matrix(
                stage.get('matrix', {}), stage.get('matrix_include', {}),
                stage.get('matrix_exclude', {}))
            buildrequests_properties = []
            for props in matrix:
                buildrequests_properties.append(props)
                props['stage_name'] = stage_name
                props['yaml_text'] = self.yaml_text
            ret.append({'stage': stage_name, 'buildrequests': buildrequests_properties})
        return ret
