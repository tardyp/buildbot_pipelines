import os

import pytest

from buildbot_pipelines import package_loader
from buildbot_pipelines.yaml_loader import PipelineYml


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
