from __future__ import absolute_import, division, print_function

import traceback

from twisted.internet import defer

from buildbot.process.buildstep import SUCCESS, BuildStep
from buildbot.steps import shell
from buildbot_pipelines.yaml_loader import PipelineYml


class ShellCommand(shell.ShellCommand):

    flunkOnFailure = True
    haltOnFailure = True
    warnOnWarnings = True

    def setupEnvironment(self, cmd):
        """ Turn all build properties into environment variables """
        shell.ShellCommand.setupEnvironment(self, cmd)
        env = {}
        for k, v in self.build.getProperties().properties.items():
            env[str(k)] = str(v[0])
        if cmd.args['env'] is None:
            cmd.args['env'] = {}
        cmd.args['env'].update(env)


class RunnerStep(BuildStep):
    MAX_NAME_LENGTH = 47
    disable = False

    def __init__(self, **kwargs):
        if "name" not in kwargs:
            kwargs['name'] = 'runner'
        self.config = None
        BuildStep.__init__(
            self,
            haltOnFailure=True,
            flunkOnFailure=True,
            **kwargs)

    def getStepConfig(self):
        pipeline_yml = self.getProperty("yaml_text")
        # @TODO load on thread
        config = PipelineYml(pipeline_yml)
        return config

    def addBBPipelineStep(self, command):
        name = None
        condition = None
        shell = "bash"
        step = None
        original_command = command
        if isinstance(command, dict):
            name = command.get("title")
            shell = command.get("shell", shell)
            condition = command.get("condition")
            step = command.get("step")
            command = command.get("cmd")

        if isinstance(command, BuildStep):
            step = command
            name = step.name

        if name is None:
            name = self.truncateName(command)
        if condition is not None:
            try:
                if not self.testCondition(condition):
                    return
            except Exception:
                self.descriptionDone = u"Problem parsing condition"
                self.addCompleteLog("condition error", traceback.format_exc())
                return

        if step is None:
            if command is None:
                self.addCompleteLog("bbtravis.yml error",
                                    "Neither step nor cmd is defined: %r" %
                                    (original_command, ))
                return

            if not isinstance(command, list):
                command = [shell, '-c', command]
            step = ShellCommand(
                name=name, description=command, command=command, doStepIf=not self.disable)
        self.build.addStepsAfterLastStep([step])

    def testCondition(self, condition):
        l = dict(
            (k, v)
            for k, (v, s) in self.build.getProperties().properties.items())
        return eval(condition, l)

    def truncateName(self, name):
        name = name.lstrip("#")
        name = name.lstrip(" ")
        name = name.split("\n")[0]
        if len(name) > self.MAX_NAME_LENGTH:
            name = name[:self.MAX_NAME_LENGTH - 3] + "..."
        return name

    @defer.inlineCallbacks
    def run(self):
        self.config = yield self.getStepConfig()
        stage = self.getProperty("stage_name")
        steps = self.config.generate_step_list(stage)
        for step in steps:
            self.addBBPipelineStep(step)

        defer.returnValue(SUCCESS)
