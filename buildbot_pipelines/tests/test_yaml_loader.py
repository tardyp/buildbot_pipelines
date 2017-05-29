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
    res = PipelineYml(android_pipeline)
    assert res.cfg != {}
    assert res.cfg['stages']['build']['steps'][1] == "!DiffManifest()"
    assert res.cfg['stages']['build']['steps'][2] == "!UploadNexus(uploads=[Interpolate(u'out/target/%(prop:TARGET)s/flashfile(.*).zip:%(prop:TARGET)s/\\\\2.zip')])"


def test_yml_k8s(k8s_pipeline):
    res = PipelineYml(k8s_pipeline)
    assert res.cfg != {}
