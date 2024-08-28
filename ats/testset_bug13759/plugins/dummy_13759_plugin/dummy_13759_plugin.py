from litp.core.plugin import Plugin
from litp.core.task import ConfigTask


class Dummy13759Plugin(Plugin):

    def create_configuration(self, api):
        # Simulate network plugin and return task for eth
        tasks = []
        ms = api.query_by_vpath("/ms")
        if0 = api.query_by_vpath("/ms/network_interfaces/if0")
        if if0 and if0.is_initial():
            tasks.append(ConfigTask(ms, if0, 'Configure eth', 'foo', 'bar'))
        elif if0 and if0.is_updated():
            tasks.append(ConfigTask(ms, if0, 'Update eth', 'fooz', 'baz'))
        return tasks

    def create_lock_tasks(self, api, node):
        ms = api.query("ms")[0]
        return (
            ConfigTask(ms, node, "lock ConfigTask", "node_lock", "blah1"),
            ConfigTask(ms, node, "unlock ConfigTask", "node_unlock", "blah2"),
        )
