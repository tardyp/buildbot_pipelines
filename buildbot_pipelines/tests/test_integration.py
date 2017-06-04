
from __future__ import absolute_import, division, print_function

import os
import shutil
import subprocess
import tempfile

from twisted.internet import defer

from buildbot.process.buildstep import SUCCESS

try:
    from buildbot.test.util.integration import RunMasterBase
except ImportError:
    print("warning")
    # if buildbot installed with wheel, it does not include the test util :-(
    RunMasterBase = object

basic_yml = """
stages:
    build:
        steps:
            - echo ok
"""


class TravisMaster(RunMasterBase):
    timeout = 300

    def mktemp(self):
        tmp = tempfile.mkdtemp(prefix="travis_trial")
        self.repo_url = repo_url = os.path.join(tmp, "repo")
        os.mkdir(repo_url)
        with open(os.path.join(repo_url, "pipeline.yml"), 'w') as f:
            f.write(basic_yml)

        subprocess.check_call("git init && git add . && git commit -m c", shell=True, cwd=repo_url)
        self.addCleanup(shutil.rmtree, tmp)
        return os.path.join(tmp, "workdir")

    @defer.inlineCallbacks
    def test_pipeline(self):
        self.mktemp()
        yield self.setupConfig(masterConfig())
        change = dict(branch="master",
                      files=["foo.c"],
                      author="me@foo.com",
                      comments="good stuff",
                      revision="HEAD",
                      category="push",
                      codebase="basic_pipeline",
                      repository=self.repo_url,
                      project="basic_pipeline"
                      )
        build = yield self.doForceBuild(wantSteps=True, useChange=change, wantLogs=True)
        self.assertEqual(build['results'], SUCCESS)


def masterConfig():
    from buildbot_pipelines import PipelineConfigurator
    c = {}
    c['configurators'] = [PipelineConfigurator()]
    return c
