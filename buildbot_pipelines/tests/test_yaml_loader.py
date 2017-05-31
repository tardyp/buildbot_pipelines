import os

import pytest

from buildbot_pipelines import package_loader
from buildbot_pipelines.yaml_loader import PipelineYml, YmlProperties


def load_example(*path):
    with open(os.path.join(
            os.path.dirname(__file__), os.path.pardir, os.path.pardir, 'examples', *path)) as f:
        return f.read()


def makeObject(typ):
    def constructor(*args, **kwargs):
        if args:
            args = [repr(a) for a in args]
        else:
            args = ["{}={}".format(k, repr(v)) for k, v in kwargs.items()]
        return "{}({})".format(typ, ", ".join(args))
    return constructor


@pytest.fixture
def basic_pipeline(monkeypatch):
    return load_example('basic', 'pipeline.yml')


@pytest.fixture
def android_pipeline(monkeypatch):
    fake_modules = {x: makeObject(x) for x in [
        "!DiffManifest", "!UploadNexus", "!DownloadNexus", "!RunAndroidTest"]}
    monkeypatch.setattr(package_loader, 'import_package', lambda _: fake_modules)
    return load_example('android', 'pipeline.yml')


@pytest.fixture
def k8s_pipeline(monkeypatch):
    fake_modules = {x: makeObject(x) for x in [
        "!DockerBuild", "!DockerUploadNexus", "!WithKubernetesInfra", "!DeployKubernetes"]}
    monkeypatch.setattr(package_loader, 'import_package', lambda _: fake_modules)
    return load_example('kubernetes_app', 'pipeline.yml')


def test_yml_android(android_pipeline):
    yml = PipelineYml(android_pipeline)
    assert yml.cfg != {}
    assert yml.cfg['stages']['build']['steps'][1] == "!DiffManifest()"
    assert yml.cfg['stages']['build']['steps'][2] == "!UploadNexus(uploads=[Interpolate(u'out/target/%(prop:TARGET)s/flashfile(.*).zip:%(prop:TARGET)s/\\\\2.zip')])"


def test_yml_k8s(k8s_pipeline):
    yml = PipelineYml(k8s_pipeline)
    assert yml.cfg != {}


def test_yml_android_trigger_push(android_pipeline):
    yml = PipelineYml(android_pipeline)
    triggers = yml.generate_triggers("codebase", "master")
    assert triggers == []


def test_yml_android_trigger_pr(android_pipeline):
    yml = PipelineYml(android_pipeline)
    triggers = yml.generate_triggers("codebase", "master", "pr")
    assert len(triggers) == 2
    assert triggers[0]['stage'] == 'build'
    assert triggers[1]['stage'] == 'test'
    assert len(triggers[0]['buildrequests']) == 5
    assert len(triggers[1]['buildrequests']) == 2
    props = triggers[1]['buildrequests'][0].asDict()
    assert props['yaml_text'][0] == android_pipeline
    del props['yaml_text']
    assert props == {
        'worker_type': ('testfarm', 'yml_worker'),
        'worker_image': ('workertestfarm-stability', 'yml_worker'),
        'worker': ({'image': 'workertestfarm-stability', 'type': 'testfarm'}, 'yml_worker'),
        'stage_name': ('test', 'yml_stage'),
        'TARGET': ('target1', 'yml_matrix'),
        'CI': (True, 'yml_global'),
        'TEST_CAMPAIGN': ('stability', 'yml_matrix'),
        'virtual_builder_name': ('codebase test TARGET:target1 TEST_CAMPAIGN:stability', 'yml_stage'),
        'virtual_builder_tags': (['codebase', 'test', 'TARGET:target1', 'TEST_CAMPAIGN:stability'], 'yml_stage')}


def test_yml_basic_trigger(basic_pipeline):
    yml = PipelineYml(basic_pipeline)
    triggers = yml.generate_triggers("codebase", "master", "pr")
    assert len(triggers) == 1
    print(triggers)
    props = triggers[0]['buildrequests'][0].asDict()
    assert props['yaml_text'][0] == basic_pipeline
    del props['yaml_text']
    assert props == {
        u'stage_name': ('tox', u'yml_stage'),
        u'virtual_builder_name': ('codebase tox', u'yml_stage'),
        u'virtual_builder_tags': (['codebase', 'tox'], u'yml_stage')}


def test_yml_android_get_steps(android_pipeline):
    yml = PipelineYml(android_pipeline)
    steps = yml.generate_step_list("build")
    assert len(steps) == 3


def test_yml_basic_get_steps(basic_pipeline):
    yml = PipelineYml(basic_pipeline)
    steps = yml.generate_step_list("tox")
    assert len(steps) == 1


def test_yml_matrix_one_var():
    res = PipelineYml.compute_matrix({'a': [1, 2]}, [], [])
    assert res == [{'a': 1}, {'a': 2}]


def test_yml_matrix_two_vars():
    res = PipelineYml.compute_matrix({'a': [1, 2], 'b': [3, 4]}, [], [])
    assert sorted(res) == sorted([{'a': 1, 'b': 3}, {'a': 2, 'b': 3}, {'a': 1, 'b': 4}, {'a': 2, 'b': 4}])


def test_yml_matrix_exclude():
    res = PipelineYml.compute_matrix({'a': [1, 2], 'b': [3, 4]}, [], [{'b': 4, 'a': 2}])
    assert sorted(res) == sorted([{'a': 1, 'b': 3}, {'a': 2, 'b': 3}, {'a': 1, 'b': 4}])


def test_yml_matrix_exclude_subset():
    res = PipelineYml.compute_matrix({'a': [1, 2], 'b': [3, 4]}, [], [{'b': 4}])
    assert sorted(res) == sorted([{'a': 1, 'b': 3}, {'a': 2, 'b': 3}])


def test_yml_matrix_include_dupe():
    res = PipelineYml.compute_matrix({'a': [1, 2], 'b': [3, 4]}, [{'b': 4, 'a': 2}])
    assert sorted(res) == sorted([{'a': 1, 'b': 3}, {'a': 2, 'b': 3}, {'a': 1, 'b': 4}, {'a': 2, 'b': 4}])


def test_yml_matrix_include_new():
    res = PipelineYml.compute_matrix({'a': [1, 2], 'b': [3, 4]}, [{'b': 4, 'a': 3}])
    assert sorted(res) == sorted([
        {'a': 1, 'b': 3}, {'a': 2, 'b': 3}, {'a': 1, 'b': 4},
        {'a': 2, 'b': 4},
        {'a': 3, 'b': 4}
        ])


def test_yml_properties_from_source():
    p = YmlProperties()
    p.setProperty('a', 1, 'A')
    p.setProperty('b', 2, 'B')
    assert p.getPropertiesForSource('B') == {'b': 2}
    assert p.getPropertiesForSource('A') == {'a': 1}
