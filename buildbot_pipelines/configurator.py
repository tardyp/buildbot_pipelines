import os

from buildbot.config import RESERVED_UNDERSCORE_NAMES, BuilderConfig
from buildbot.configurators import ConfiguratorBase
from buildbot.interfaces import ILatentWorker
from buildbot.process import factory
from buildbot.process.properties import Property
from buildbot.schedulers.triggerable import Triggerable
from buildbot.steps.source.git import Git
from buildbot_pipelines.schedulers.anycodebasescheduler import \
    AnyCodeBaseScheduler
from buildbot_pipelines.steps.runner import RunnerStep
from buildbot_pipelines.steps.spawner import SpawnerStep

RESERVED_UNDERSCORE_NAMES.extend(["__spawner", "__runner"])


class PipelineConfigurator(ConfiguratorBase):

    def get_all_workers(self):
        workers = [s.workername for s in self.config[
            'workers']]
        return workers

    def get_spawner_workers(self):
        workers = [s.workername for s in self.config[
            'workers'] if not ILatentWorker.providedBy(s)]
        if not workers:
            return self.get_all_workers()
        return workers

    def get_runner_workers(self):
        workers = [s.workername for s in self.config[
            'workers'] if ILatentWorker.providedBy(s)]
        if not workers:
            return self.get_all_workers()
        return workers

    def configure(self, config_dict):
        c = self.config = config_dict
        PORT = int(os.environ.get('PORT', 8010))
        c.setdefault(
            'buildbotURL',
            os.environ.get('buildbotURL', "http://localhost:%d/" % (PORT, )))

        db_url = os.environ.get('BUILDBOT_DB_URL')
        if db_url is not None:
            self.config.setdefault('db', {'db_url': db_url})

        # minimalistic config to activate new web UI
        c.setdefault('www', dict(port=PORT,
                        plugins=dict(
                        console_view=True, waterfall_view=True),
                      ))
        c.setdefault('protocols', {'pb': {'port': 9989}})
        c.setdefault('builders', [])
        c.setdefault('schedulers', [])

        # Define the builder for the main job
        f = factory.BuildFactory()
        f.addStep(Git(repourl=Property("repository"), codebase=Property("codebase"), name='git', shallow=1))
        f.addStep(SpawnerStep())

        self.config['builders'].append(BuilderConfig(
            name='__spawner',
            workernames=self.get_spawner_workers(),
            collapseRequests=False,
            factory=f
        ))
        self.config['schedulers'].append(AnyCodeBaseScheduler(
            name='__spawner',
            builderNames=['__spawner']
        ))

        # Define the builder for the main job
        f = factory.BuildFactory()
        f.addStep(RunnerStep())

        self.config['builders'].append(BuilderConfig(
            name='__runner',
            workernames=self.get_runner_workers(),
            collapseRequests=False,
            factory=f
        ))
        self.config['schedulers'].append(Triggerable(
            name='__runner',
            builderNames=['__runner'],
            codebases={},
        ))
