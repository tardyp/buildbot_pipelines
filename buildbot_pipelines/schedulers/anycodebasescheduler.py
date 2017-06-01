from twisted.internet import defer
from twisted.python import log

from buildbot.changes import changes
from buildbot.process.properties import Properties
from buildbot.schedulers.basic import AnyBranchScheduler


# Note this code copy paste too much from the base scheduler
# the base scheduler is not really planned to make on scheduler for all codebases
# so we need to do it that way for now.
# need pipeline concept to settle a bit to see if this is the right approach.

class AnyCodeBaseScheduler(AnyBranchScheduler):

    @defer.inlineCallbacks
    def _changeCallback(self, key, msg, fileIsImportant, change_filter,
                        onlyImportant):

        # ignore changes delivered while we're not running
        if not self._change_consumer:
            return

        # get a change object, since the API requires it
        chdict = yield self.master.db.changes.getChange(msg['changeid'])
        change = yield changes.Change.fromChdict(self.master, chdict)

        # filter it
        if change_filter and not change_filter.filter_change(change):
            return
        if change.codebase not in self.codebases:
            self.codebases[change.codebase] = {}

        # use change_consumption_lock to ensure the service does not stop
        # while this change is being processed
        d = self._change_consumption_lock.run(
            self.gotChange, change, True)
        d.addErrback(log.err, 'while processing change')

    @defer.inlineCallbacks
    def addBuildsetForChanges(self, waited_for=False, reason='',
                              external_idstring=None, changeids=None, builderNames=None,
                              properties=None,
                              **kw):
        if changeids is None:
            changeids = []
        changesByCodebase = {}

        def get_last_change_for_codebase(codebase):
            return max(changesByCodebase[codebase], key=lambda change: change["changeid"])

        # Changes are retrieved from database and grouped by their codebase
        for changeid in changeids:
            chdict = yield self.master.db.changes.getChange(changeid)
            changesByCodebase.setdefault(chdict["codebase"], []).append(chdict)

        sourcestamps = []
        for codebase in sorted(self.codebases):
            if codebase not in changesByCodebase:
                # normal scheduler will set one ss by known codebase.
                # we only want a ss per change.
                continue
            else:
                lastChange = get_last_change_for_codebase(codebase)
                ss = lastChange['sourcestampid']
            sourcestamps.append(ss)

        # hack to set virtual builder name for __spawner builder
        if properties is None:
            properties = Properties()
        properties.setProperty("virtual_builder_name", lastChange['codebase'] + '-' + lastChange['category'], 'scheduler')
        properties.setProperty("virtual_builder_tags", [lastChange['codebase'], lastChange['category']], 'scheduler')
        # add one buildset, using the calculated sourcestamps
        bsid, brids = yield self.addBuildsetForSourceStamps(
            waited_for, sourcestamps=sourcestamps, reason=reason,
            external_idstring=external_idstring, builderNames=builderNames,
            properties=properties, **kw)

        defer.returnValue((bsid, brids))
