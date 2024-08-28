from litp.core.plugin import Plugin
from litp.core.task import ConfigTask
from litp.core.task import CallbackTask
from litp.plan_types.deployment_plan import deployment_plan_tags


class Dummy114663Plugin(Plugin):

    def create_configuration(self, api):
        # Simulate network plugin and return task for eth
        tasks = []
        for node in api.query('node', is_initial=True):
            install_task = CallbackTask(
                node,
                "Installing node \"%s\"" % node.hostname,
                self._cb_install_node
            )
            install_task.tag_name = deployment_plan_tags.BOOT_TAG
            tasks.append(install_task)

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

    def _cb_install_node(self, cb_api):
        pass
