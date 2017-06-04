from __future__ import absolute_import, division, print_function

from twisted.internet import defer

from buildbot.process.buildstep import SUCCESS, BuildStep, BuildStepFailed
from buildbot.steps.trigger import Trigger
from buildbot.steps.worker import CompositeStepMixin
from buildbot_pipelines.yaml_loader import PipelineYml, PipelineYmlInvalid


HOW_TO_DEBUG = """
In order to help you debug, you can install the bbpipeline tool:

virtualenv sandbox
. ./sandbox/bin/activate
pip install buildbot_pipelines
bbpipeline run
"""


class MultiplePropertyTrigger(Trigger):

    def __init__(self, schedulers_and_properties, **kwargs):
        self.schedulers_and_properties = schedulers_and_properties
        Trigger.__init__(self, schedulerNames=["dummy"], updateSourceStamp=False, waitForFinish=True, **kwargs)

    def getResultSummary(self):
        return {u'step': "stage " + self.name + " done"}

    def getCurrentSummary(self):
        return {u'step': "running stage " + self.name}

    def getSchedulersAndProperties(self):
        return self.schedulers_and_properties

    def createTriggerProperties(self, properties):
        return properties


class SpawnerStep(BuildStep, CompositeStepMixin):
    def __init__(self, **kwargs):
        if "name" not in kwargs:
            kwargs['name'] = 'trigger'
        self.config = None
        BuildStep.__init__(
            self,
            haltOnFailure=True,
            flunkOnFailure=True,
            **kwargs)

    def addHelpLog(self):
        self.addCompleteLog("help.txt", HOW_TO_DEBUG)

    @defer.inlineCallbacks
    def getStepConfig(self):
        pipeline_yml = None
        for filename in [".pipeline.yml", "pipeline.yml"]:
            try:
                pipeline_yml = yield self.getFileContentFromWorker(filename, abandonOnFailure=True)
                break
            except BuildStepFailed as e:
                continue

        if pipeline_yml is None:
            self.descriptionDone = u"unable to fetch .pipeline.yml"
            self.addCompleteLog(
                "error",
                "Please put a file named .pipeline.yml at the root of your repository:\n{0}".format(e))
            self.addHelpLog()
            raise

        self.addCompleteLog(filename, pipeline_yml)

        # @TODO load on thread
        try:
            config = PipelineYml(pipeline_yml)
        except PipelineYmlInvalid as e:
            self.descriptionDone = u"bad .pipeline.yml"
            self.addCompleteLog(
                "error",
                ".pipeline.yml is invalid:\n{0}".format(e))
            self.addHelpLog()
            raise BuildStepFailed("Bad pipeline file")
        defer.returnValue(config)

    @defer.inlineCallbacks
    def run(self):
        self.config = yield self.getStepConfig()
        changes = list(self.build.allChanges())
        if changes:
            # @TODO handle the cron case
            change = changes[-1]
            branch = change.branch
            codebase = change.codebase
            category = change.category
            triggers = self.config.generate_triggers(codebase, branch, category)
            self.build.addStepsAfterLastStep([
                MultiplePropertyTrigger(
                    [{'sched_name': '__runner', 'props_to_set': props, 'unimportant': False}
                        for props in trigger['buildrequests']],
                    name=trigger['stage']
                )
                for trigger in triggers])
        defer.returnValue(SUCCESS)
