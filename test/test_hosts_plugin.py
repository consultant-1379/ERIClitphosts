import unittest

from collections import defaultdict
from litp.core.model_manager import ModelManager
from litp.core.plugin_manager import PluginManager
from litp.core.plugin_context_api import PluginApiContext
from litp.extensions.core_extension import CoreExtension
from litp.core.task import ConfigTask
from hosts_extension.hosts_extension import HostsExtension
from hosts_plugin.hosts_plugin import HostsPlugin, _applied_all_aliasnames
from network_extension.network_extension import NetworkExtension
from litp.core.validators import ValidationError
from litp.core import constants
from mock import MagicMock, Mock, patch, call
import socket

from litp.core.translator import Translator
t = Translator('ERIClitphosts_CXP9030589')
_ = t._


class TestHostsPlugin(unittest.TestCase):

    def setUp(self):
        self.model = ModelManager()
        self.plugin_manager = PluginManager(self.model)
        self.context = PluginApiContext(self.model)
        self.plugin_manager.add_property_types(
            CoreExtension().define_property_types())
        self.plugin_manager.add_item_types(
            CoreExtension().define_item_types())
        self.plugin = HostsPlugin()
        self.plugin_manager.add_property_types(
            NetworkExtension().define_property_types())
        self.plugin_manager.add_item_types(
            NetworkExtension().define_item_types())
        self.plugin_manager.add_property_types(
            HostsExtension().define_property_types())
        self.plugin_manager.add_item_types(
            HostsExtension().define_item_types())
        self.plugin_manager.add_plugin('TestPlugin', 'some.test.plugin',
                                       '1.0.0', self.plugin)

    def _create_standard_4th_node_item(self):
        self.sys4_url = "/infrastructure/systems/system4"
        self.node4_url = "/deployments/local_vm/clusters/cluster1/nodes/node4"

        node4 = self.model.create_item("node",
                                       self.node4_url,
                                       hostname="node4")

        self.model.create_item('eth',
                               self.node4_url + "/network_interfaces/if0",
                               network_name="mgmt",
                               device_name="eth0",
                               ipaddress="10.0.4.1",
                               macaddress='08:00:27:4B:C1:3F')

        self.model.create_item('eth',
                               self.node4_url + "/network_interfaces/if1",
                               network_name="heartbleed",
                               device_name="eth1",
                               ipaddress="10.0.4.2",
                               macaddress='08:00:27:4B:C1:3F')

        self.model.create_item('vbox-system',
                               self.sys4_url,
                               system_name="MN4VM")
        self.model.create_inherited(self.sys4_url,
                                    self.node4_url + "/system")

        return node4

    def _create_standard_items_ok(self):
        self.sys1_url = "/infrastructure/systems/system1"
        self.sys2_url = "/infrastructure/systems/system2"
        self.sys3_url = "/infrastructure/systems/system3"
        self.cluster_url = "/deployments/local_vm/clusters/cluster1"
        self.node1_url = "/deployments/local_vm/clusters/cluster1/nodes/node1"
        self.node2_url = "/deployments/local_vm/clusters/cluster1/nodes/node2"
        self.node3_url = "/deployments/local_vm/clusters/cluster1/nodes/node3"
        self.model.create_root_item("root", "/")
        self.model.create_item('deployment', '/deployments/local_vm')
        self.model.create_item('cluster', self.cluster_url)

        # Nodes
        node1 = self.model.create_item("node", self.node1_url,
                            hostname="node1")
        node2 = self.model.create_item("node", self.node2_url,
                            hostname="node2")
        node3 = self.model.create_item("node", self.node3_url,
                            hostname="node3")

        # new network model
        self.model.create_item(
            'network',
            '/infrastructure/networking/networks/mgmt_network',
            name='mgmt',
            subnet='10.0.1.0/24',
            litp_management='true'
            )
        self.model.create_item(
            'network',
            '/infrastructure/networking/networks/hrbt_ntwk',
            name='heartbleed',
            subnet='10.0.2.0/24'
            )

        # MS NIC
        self.model.create_item(
            'eth',
            '/ms/network_interfaces/if0',
            network_name="mgmt",
            device_name="eth0",
            ipaddress="10.0.1.10",
            macaddress='08:00:27:5B:C1:3F'
            )

        # Node 1 NICs
        self.model.create_item(
            'eth',
            self.node1_url + "/network_interfaces/if0",
            network_name="mgmt",
            device_name="eth0",
            ipaddress="10.0.1.0",
            macaddress='08:00:27:5B:C1:3F'
            )
        self.model.create_item(
            'eth',
            self.node1_url + "/network_interfaces/if1",
            network_name="heartbleed",
            device_name="eth1",
            ipaddress="10.0.2.0",
            macaddress='08:00:27:5B:C1:3F'
            )
        # Node 2 NICs
        self.model.create_item(
            'eth',
            self.node2_url + "/network_interfaces/if0",
            network_name="mgmt",
            device_name="eth0",
            macaddress='08:00:27:65:C2:1D',
            ipaddress="10.0.1.1"
            )
        self.model.create_item(
            'eth',
            self.node2_url + "/network_interfaces/if1",
            network_name="heartbleed",
            device_name="eth1",
            macaddress='08:00:27:48:A8:B4',
            ipaddress="10.0.2.1"
            )
        # Node 3 NICs
        self.model.create_item(
            'eth',
            self.node3_url + "/network_interfaces/if0",
            network_name="mgmt",
            device_name="eth0",
            ipaddress="10.0.1.2",
            macaddress='08:00:27:23:C3:B3'
            )
        self.model.create_item(
            'eth',
            self.node3_url + "/network_interfaces/if1",
            network_name="heartbleed",
            device_name="eth1",
            macaddress='08:00:27:63:73:53',
            ipaddress="10.0.2.2"
            )

        self.model.create_item('vbox-system', self.sys1_url,
                                        system_name="MN1VM")
        self.model.create_item('vbox-system', self.sys2_url,
                                     system_name="MN2VM")
        self.model.create_item('vbox-system', self.sys3_url,
                                        system_name="MN3VM")
        self.model.create_inherited(self.sys1_url, node1.get_vpath() + \
                                       "/system")
        self.model.create_inherited(self.sys2_url, node2.get_vpath() + \
                                       "/system")
        self.model.create_inherited(self.sys3_url, node3.get_vpath() + \
                                       "/system")

    def _create_standard_items_clusters_ok(self):
        self.sys1_url = "/infrastructure/systems/system1"
        self.sys2_url = "/infrastructure/systems/system2"
        self.sys3_url = "/infrastructure/systems/system3"
        self.cluster_url1 = "/deployments/local_vm/clusters/cluster1"
        self.cluster_url2 = "/deployments/local_vm/clusters/cluster2"
        self.node1_url = "/deployments/local_vm/clusters/cluster1/nodes/node1"
        self.node2_url = "/deployments/local_vm/clusters/cluster1/nodes/node2"
        self.node3_url = "/deployments/local_vm/clusters/cluster2/nodes/node3"
        self.model.create_root_item("root", "/")
        self.model.create_item('deployment', '/deployments/local_vm')
        self.model.create_item('cluster', self.cluster_url1)
        self.model.create_item('cluster', self.cluster_url2)

        # Nodes
        node1 = self.model.create_item("node", self.node1_url,
                            hostname="node1")
        node2 = self.model.create_item("node", self.node2_url,
                            hostname="node2")
        node3 = self.model.create_item("node", self.node3_url,
                            hostname="node3")

        # new network model
        self.model.create_item(
            'network',
            '/infrastructure/networking/networks/mgmt_network',
            name='mgmt',
            subnet='10.0.1.0/24',
            litp_management='true'
            )
        self.model.create_item(
            'network',
            '/infrastructure/networking/networks/hrbt_ntwk',
            name='heartbleed',
            subnet='10.0.2.0/24'
            )
        # MS NIC
        self.model.create_item(
            'eth',
            '/ms/network_interfaces/if0',
            network_name="mgmt",
            device_name="eth0",
            ipaddress="10.0.1.10",
            macaddress='08:00:27:5B:C1:3F'
            )
        # Node 1 NICs
        self.model.create_item(
            'eth',
            self.node1_url + "/network_interfaces/if0",
            network_name="mgmt",
            device_name="eth0",
            ipaddress="10.0.1.0",
            macaddress='08:00:27:5B:C1:3F'
            )
        self.model.create_item(
            'eth',
            self.node1_url + "/network_interfaces/if1",
            network_name="heartbleed",
            device_name="eth1",
            ipaddress="10.0.2.0",
            macaddress='08:00:27:5B:C1:3F'
            )
        # Node 2 NICs
        self.model.create_item(
            'eth',
            self.node2_url + "/network_interfaces/if0",
            network_name="mgmt",
            device_name="eth0",
            macaddress='08:00:27:65:C2:1D',
            ipaddress="10.0.1.1"
            )
        self.model.create_item(
            'eth',
            self.node2_url + "/network_interfaces/if1",
            network_name="heartbleed",
            device_name="eth1",
            macaddress='08:00:27:48:A8:B4',
            ipaddress="10.0.2.1"
            )
        # Node 3 NICs
        self.model.create_item(
            'eth',
            self.node3_url + "/network_interfaces/if0",
            network_name="mgmt",
            device_name="eth0",
            ipaddress="10.0.1.2",
            macaddress='08:00:27:23:C3:B3'
            )
        self.model.create_item(
            'eth',
            self.node3_url + "/network_interfaces/if1",
            network_name="heartbleed",
            device_name="eth1",
            macaddress='08:00:27:63:73:53',
            ipaddress="10.0.2.2"
            )
        self.model.create_item('vbox-system', self.sys1_url,
                                        system_name="MN1VM")
        self.model.create_item('vbox-system', self.sys2_url,
                                     system_name="MN2VM")
        self.model.create_item('vbox-system', self.sys3_url,
                                        system_name="MN3VM")
        self.model.create_inherited(self.sys1_url, node1.get_vpath() + \
                                       "/system")
        self.model.create_inherited(self.sys2_url, node2.get_vpath() + \
                                       "/system")
        self.model.create_inherited(self.sys3_url, node3.get_vpath() + \
                                       "/system")
        # alias-node-config
        self.model.create_item("alias-node-config",
            "/deployments/local_vm/clusters/cluster2"
            "/nodes/node3/configs/aliasconf")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster2/nodes"
            "/node3/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="localhost")
        # alias-cluster-config
        self.model.create_item(
            "alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1"
                "/configs/aliasconf")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master2",
            address="11.11.11.2", alias_names="master2")

        self.model.create_item("alias-node-config",
            "/ms/configs/aliasconf")
        self.model.create_item("alias",
            "/ms/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1,slave1")

    def test_applied_all_alias_names(self):
        # TORF-125307: Check applied_properties and not the properties dict
        self._create_standard_items_ok()

        self.model.create_item("alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf")
        alias_mi = self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")
        alias_qi = self.context.query("alias")[0]

        # alias_names property not in applied properties
        self.assertEqual("master1", alias_qi.alias_names)
        self.assertTrue(alias_qi.alias_names not in alias_qi.applied_properties)

        # KeyError not thown now as we don't use the dot notation here
        self.assertEqual([], _applied_all_aliasnames(alias_qi))

        # alias item is now applied ('alias_names' is now in applied_properties)
        alias_mi.set_applied()
        self.assertEqual(["master1"], _applied_all_aliasnames(alias_qi))

    @patch.object(HostsPlugin, '_create_alias_task')
    @patch.object(HostsPlugin, '_any_updated_duplicates', Mock(return_value=False))
    def test_create_state_tasks_apd_false(self, mock_create_alias_task):
        # TORF-125307: If APD=False, don't use applied properties
        self._create_standard_items_ok()

        self.model.create_item("alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf")
        alias_mi = self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1,master2,master3")
        alias_mi.set_for_removal()
        node_qi = self.context.query("node")[0]
        node_qi._model_item.set_applied()
        cluster_qi = self.context.query("cluster")[0]
        alias_qi = self.context.query("alias")[0]

        self.assertEqual({}, alias_qi.applied_properties)

        # Item was never applied, e.g Initial APD=False -> ForRemoval
        # Create one deconfigure task
        self.plugin._create_state_tasks(self.context, node_qi, alias_qi, cluster_qi.item_id)
        # Tests available_hostname(), available_aliasnames(), available_property()
        self.assertEquals(1, mock_create_alias_task.call_count)
        desc = 'Remove "master1,master2,master3" alias(es) from node "node1"'
        expected = [call("cluster1", node_qi, alias_qi, "master1",
            ["master2", "master3"], "11.11.11.1", desc, ensure="absent")]
        self.assertEqual(expected, mock_create_alias_task.call_args_list)

        mock_create_alias_task.reset_mock()
        # Item was never applied, e.g Initial APD=False -> Updated
        # Create two tasks, one to deconfig the other to config
        alias_mi.set_updated()
        self.plugin._create_state_tasks(self.context, node_qi, alias_qi, cluster_qi.item_id)
        self.assertEquals(2, mock_create_alias_task.call_count)
        # Tests safe_applied_hostname()
        # deconfig task
        desc = 'Remove "master1" alias from node "node1"'
        expected = call("cluster1", node_qi, alias_qi, "master1",
            ["master2", "master3"], "11.11.11.1", desc, ensure="absent")
        self.assertEqual(expected, mock_create_alias_task.call_args_list[0])
        # config task
        desc = 'Update node "node1" host file with "master1,master2,master3" alias(es)'
        expected = call("cluster1", node_qi, alias_qi, "master1",
            ["master2", "master3"], "11.11.11.1", desc, model_items=None)
        self.assertEqual(expected, mock_create_alias_task.call_args_list[1])

    def test_create_cfg(self):
        self._create_standard_items_ok()
        config_tasks = self.plugin.create_configuration(self.context)
        self.assertEqual('hosts::replacehost', config_tasks[0].call_type)
        self.assertEqual('hosts::hostentry', config_tasks[1].call_type)
        self.assertNotEqual('abc::entry', config_tasks[1].call_type)
        self.assertNotEqual('Task Desc', config_tasks[1].description)
        self.assertNotEqual('xx::entry', config_tasks[2].call_type)
        self.assertEqual(
            'Created by LITP. Please do not edit',
            config_tasks[1].kwargs['comment'])
        self.assertEqual(20, len(config_tasks))

    def test__should_update_hosts_file(self):
        # ip address is updated
        class MockNetInterfaceUpdatedIp(object):
            def __init__(self):
                self.network_name = 'mgmt'
                self.applied_properties = {'ipaddress': '1.2.3.4'}
                self.ipaddress = '1.2.3.5'

            def is_updated(self):
                return True

            def is_initial(self):
                return False

        # ip is not updated but the range is. is_updated returns true
        # for a range update regardless of ip update
        class MockNetInterfaceSameIp(object):
            def __init__(self):
                self.network_name = 'mgmt'
                self.applied_properties = {'ipaddress': '1.2.3.4'}
                self.ipaddress = '1.2.3.4'
                self.applied_properties_determinable = True

            def is_updated(self):
                return True

            def is_initial(self):
                return False

        class MockNetInterfaceNoChanges(object):
            def __init__(self):
                self.network_name = 'mgmt'
                self.applied_properties = {'ipaddress': '1.2.3.4'}
                self.ipaddress = '1.2.3.4'
                self.applied_properties_determinable = True

            def is_updated(self):
                return False

            def is_initial(self):
                return False

        class MockNetInterfaceAddrRemoved(object):
            def __init__(self):
                self.network_name = 'mgmt'
                self.applied_properties = MagicMock()
                self.applied_properties.ipaddress = '1.2.3.4'
                self.ipaddress = None
                self.applied_properties_determinable = True

            def is_updated(self):
                return True

            def is_initial(self):
                return False

        class MockNetInterfaceIpAddedUpdated(object):
            def __init__(self):
                self.network_name = 'mgmt'
                self.applied_properties = None
                self.ipaddress = '1.2.3.5'
                self.applied_properties_determinable = True

            def is_updated(self):
                return True

            def is_initial(self):
                return False

        class MockNetInterfaceIpAddedInitial(object):
            def __init__(self):
                self.network_name = 'mgmt'
                self.applied_properties = None
                self.ipaddress = '1.2.3.5'
                self.applied_properties_determinable = True

            def is_updated(self):
                return False

            def is_initial(self):
                return True

        class MockNetInterfaceAppliedNotDeterminable(object):
            def __init__(self):
                self.network_name = 'mgmt'
                self.applied_properties = {'ipaddress': '1.2.3.4'}
                self.ipaddress = '1.2.3.4'
                self.applied_properties_determinable = False

            def is_updated(self):
                return False

            def is_initial(self):
                return False

        class MockNode(object):
            def __init__(self):
                self.network_interfaces = [MockNetInterfaceUpdatedIp()]

        class MockNode2(object):
            def __init__(self):
                self.network_interfaces = [MockNetInterfaceSameIp()]

        class MockNode3(object):
            def __init__(self):
                self.network_interfaces = [MockNetInterfaceNoChanges()]

        class MockNode4(object):
            def __init__(self):
                self.network_interfaces = [MockNetInterfaceAddrRemoved(), \
                                           MockNetInterfaceIpAddedInitial()]

        class MockNode5(object):
            def __init__(self):
                self.network_interfaces = [MockNetInterfaceAddrRemoved(), \
                                           MockNetInterfaceIpAddedUpdated()]

        class MockNode6(object):
            def __init__(self):
                self.network_interfaces = [MockNetInterfaceAppliedNotDeterminable()]

        network_name = 'mgmt'
        node = MockNode()
        result = HostsPlugin._should_update_hosts_file(node, network_name)
        self.assertTrue(result)

        node2 = MockNode2()
        self.assertFalse(HostsPlugin._should_update_hosts_file(node2,
                                                           network_name))

        node3 = MockNode3()
        self.assertFalse(HostsPlugin._should_update_hosts_file(node3,
                                                           network_name))

        node4 = MockNode4()
        self.assertTrue(HostsPlugin._should_update_hosts_file(node4,
                                                           network_name))

        node5 = MockNode5()
        self.assertTrue(HostsPlugin._should_update_hosts_file(node5,
                                                           network_name))

        node6 = MockNode6()
        self.assertTrue(HostsPlugin._should_update_hosts_file(node6,
                                                           network_name))

    def test_alias_service(self):
        self._create_standard_items_ok()

        self.model.create_item("deployment", "/deployments/local_vm")
        self.model.create_item(
            "cluster", "/deployments/local_vm/clusters/cluster1")
        self.model.create_item("alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")

        node1 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1")
        node2 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node2")
        node3 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node3")

        alias = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1")

        tasks = self.plugin.create_configuration(self.context)
        self.assertEquals(set([
            ConfigTask(node1, alias,
                'Update node "node1" host file with "master1" alias',
                'hosts::hostentry',
                'cluster1_node1_master1',
                name="master1",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),
            ConfigTask(node2, alias,
                'Update node "node2" host file with "master1" alias',
                'hosts::hostentry',
                'cluster1_node2_master1',
                name="master1",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),
            ConfigTask(node3, alias,
                'Update node "node3" host file with "master1" alias',
                'hosts::hostentry',
                'cluster1_node3_master1',
                name="master1",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),
        ]), set(tasks[-3:]))

    def test_update_alias(self):
        self._create_standard_items_ok()

        self.model.create_item("deployment", "/deployments/local_vm")
        self.model.create_item(
            "cluster", "/deployments/local_vm/clusters/cluster1")
        self.model.create_item("alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")

        self.model.update_item(
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="22.22.22.2")

        node1 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1")
        node2 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node2")
        node3 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node3")

        alias = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1")

        tasks = self.plugin.create_configuration(self.context)

        new_tasks = [
            ConfigTask(node1, alias,
                'Update node "node1" host file with "master1" alias',
                'hosts::hostentry',
                'cluster1_node1_master1',
                name="master1",
                ip="22.22.22.2",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),
            ConfigTask(node2, alias,
                'Update node "node2" host file with "master1" alias',
                'hosts::hostentry',
                'cluster1_node2_master1',
                name="master1",
                ip="22.22.22.2",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),
            ConfigTask(node3, alias,
                'Update node "node3" host file with "master1" alias',
                'hosts::hostentry',
                'cluster1_node3_master1',
                name="master1",
                ip="22.22.22.2",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),

        ]
        [self.assertTrue(t in tasks) for t in new_tasks]

    def test_create_ms_alias(self):
        self._create_standard_items_ok()

        ms = self.context.query_by_vpath("/ms")

        self.model.create_item("alias-node-config",
            "/ms/configs/aliasconf")
        self.model.create_item("alias",
            "/ms/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1,slave1")

        alias = self.context.query_by_vpath(
            "/ms/configs/aliasconf/aliases/master1")

        tasks = self.plugin.create_configuration(self.context)
        self.assertTrue(
            ConfigTask(ms, alias,
                'Update node "{0}" host file with "master1,slave1" alias(es)'.format(ms.hostname),
                'hosts::hostentry',
                '_{0}_master1'.format(ms.hostname),
                name="master1",
                ip="11.11.11.1",
                host_aliases=['slave1'],
                comment='Created by LITP. Please do not edit',
                ensure='present',
            )
        in tasks)

        self.model.update_item(
            "/ms/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")
        tasks = self.plugin.create_configuration(self.context)

        self.assertTrue(
            ConfigTask(ms, alias,
                'Update node "{0}" host file with "master1" alias(es)'.format(ms.hostname),
                'hosts::hostentry',
                '_{0}_master1'.format(ms.hostname),
                name="master1",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='present',
            )
        in tasks)

    def test_add_fqdn_node(self):
        self._create_standard_items_ok()
        self.model.update_item(self.node1_url, domain="initial.com")

        node1_iface = self.context.query_by_vpath(self.node1_url + "/network_interfaces/if0")
        node1 = self.context.query_by_vpath(self.node1_url)

        node1_iface._model_item.set_applied()
        node1._model_item.set_applied()

        self.model.update_item(self.node1_url, domain="updated.com")
        node1._model_item.set_updated()

        tasks = self.plugin.create_configuration(self.context)
        fqdn = node1.hostname + "." + node1.domain + "\t" + node1.hostname
        self.assertTrue(
            ConfigTask(node1, node1_iface,
                       'Update node "%s" host file with FQDN' % node1.hostname,
                       'hosts::replacehost',
                       node1.hostname,
                       fqdn=fqdn)
            in tasks)

    def test_remove_fqdn_node(self):
        self._create_standard_items_ok()
        self.model.update_item(self.node1_url, domain="initial.com")

        node1_iface = self.context.query_by_vpath(self.node1_url + "/network_interfaces/if0")
        node1 = self.context.query_by_vpath(self.node1_url)

        node1_iface._model_item.set_applied()
        node1._model_item.set_applied()

        self.model.update_item(self.node1_url, domain=None)
        node1._model_item.set_updated()

        tasks = self.plugin.create_configuration(self.context)
        fqdn = ""
        self.assertTrue(
            ConfigTask(node1, node1_iface,
                       'Update node "%s" host file with FQDN' % node1.hostname,
                       'hosts::replacehost',
                       node1.hostname,
                       fqdn=fqdn)
            in tasks)

    def test_reapply_same_fqdn_on_node(self):
        self._create_standard_items_ok()
        self.model.update_item(self.node1_url, domain="initial.com")

        node1_iface = self.context.query_by_vpath(self.node1_url + "/network_interfaces/if0")
        node1 = self.context.query_by_vpath(self.node1_url)

        node1_iface._model_item.set_applied()
        node1._model_item.set_applied()

        self.model.update_item(self.node1_url, domain="initial.com")
        # Set the node state to initial so that a task will be created for the
        # FQDN domain property.
        node1._model_item.set_initial()

        tasks = self.plugin.create_configuration(self.context)
        fqdn = node1.hostname + "." + node1.domain + "\t" + node1.hostname

        # FYI: The 'description' parameter of the task isn't exaluated as part
        # of the task.__eq__ method.
        self.assertTrue(
            ConfigTask(node1, node1_iface,
                       'Update node "%s" host file with FQDN' % node1.hostname,
                       'hosts::replacehost',
                       node1.hostname,
                       fqdn=fqdn)
            in tasks)

    def test_update_hostname(self):
        self._create_standard_items_ok()

        self.model.create_item("deployment", "/deployments/local_vm")
        i1 = self.model.create_item(
            "cluster", "/deployments/local_vm/clusters/cluster1")
        i2 = self.model.create_item("alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf")
        i3 = self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")

        self.model.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1").set_applied()
        self.model.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1").set_applied()
        self.model.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node2").set_applied()
        self.model.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node3").set_applied()

        i2.set_applied()
        i3.set_applied()

        self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1/nodes/node3")

        self.model.update_item(
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            alias_names="master2")

        node1 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1")

        node2 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node2")

        alias = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1")

        tasks = self.plugin.create_configuration(self.context)

        new_tasks = [
            ConfigTask(node1, alias,
                'Remove "master1" alias from node "node1"',
                'hosts::hostentry',
                'cluster1_node1_master1',
                name="master1",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='absent',
                ),
            ConfigTask(node1, alias,
                'Update node "node1" host file with "master2" alias',
                'hosts::hostentry',
                'cluster1_node1_master2',
                name="master2",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),
            ConfigTask(node2, alias,
                'Remove "master1" alias from node "node2"',
                'hosts::hostentry',
                'cluster1_node2_master1',
                name="master1",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='absent',
                ),
            ConfigTask(node2, alias,
                'Update node "node2" host file with "master2" alias',
                'hosts::hostentry',
                'cluster1_node2_master2',
                name="master2",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),
        ]

        [self.assertTrue(t in tasks) for t in new_tasks]

        node1._model_item.set_applied()
        node2._model_item.set_applied()
        alias._model_item.set_applied()

        self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1/nodes/node2")

        self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1/nodes/node3")

        self.model.update_item(
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            alias_names="masternew")

        tasks = self.plugin.create_configuration(self.context)

        new_tasks = [
            ConfigTask(node1, alias,
                'Remove "master2" alias from node "node1"',
                'hosts::hostentry',
                'cluster1_node1_master2',
                name="master2",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='absent',
                ),
            ConfigTask(node1, alias,
                'Update node "node1" host file with "masternew" alias',
                'hosts::hostentry',
                'cluster1_node1_masternew',
                name="masternew",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ),
        ]
        [self.assertTrue(t in set(tasks)) for t in new_tasks]

    def test_update_node_alias(self):
        self._create_standard_items_ok()
        self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1/nodes/node2")
        self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1/nodes/node3")

        self.model.create_item("alias-node-config",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")

        node1 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1")

        alias = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/aliasconf/aliases/master1")

        tasks = self.plugin.create_configuration(self.context)

        self.assertEquals(
            ConfigTask(node1, alias,
                'Update node "node1" host file with "master1" alias',
                'hosts::hostentry',
                '_node1_master1',
                name="master1",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='present',
                ), tasks[-1])

    def testValidateAliasesRestrictedList(self):
        self._create_standard_items_ok()

        self.model.create_item("alias-node-config",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="localhost")

        # localhost is restricted
        result = self.plugin.validate_model(self.context)
        self.assertEquals(ValidationError(property_name="alias_names",
            error_message='Restricted alias name "localhost"'
                ' found at /deployments/local_vm/clusters/cluster1/nodes'
                '/node1/configs/aliasconf/aliases/master1'), result[0])

        # Validate no hostnames used by nodes
        self.model.update_item(
            "/deployments/local_vm/clusters/cluster1/nodes/node1"
            "/configs/aliasconf/aliases/master1",
            alias_names="node1")
        result = self.plugin.validate_model(self.context)
        self.assertEquals(ValidationError(property_name="alias_names",
            error_message='Restricted alias name "node1"' \
                ' found at /deployments/local_vm/clusters/cluster1/nodes'
                '/node1/configs/aliasconf/aliases/master1'), result[0])

    def testValidateDuplicates(self):
        self._create_standard_items_ok()

        self.model.create_item(
            "alias-node-config",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf")
        self.model.create_item(
            "alias",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf/aliases/master1",
            address="11.11.11.1",
            alias_names="master1")
        self.model.create_item(
            "alias",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf/aliases/master2",
            address="11.11.11.2",
            alias_names="master1")

        result = self.plugin.validate_model(self.context)
        self.assertEquals(ValidationError(
            item_path="/deployments/local_vm/clusters/cluster1/nodes/node1",
            property_name="alias_name",
            error_message='Duplicate alias for master1 found at '
                '/deployments/local_vm/clusters/cluster1/nodes'
                '/node1/configs/aliasconf/aliases/master1, '
                '/deployments/local_vm/clusters/cluster1/nodes'
                '/node1/configs/aliasconf/aliases/master2'), result[0])

    def testValidateDuplicates_TORF_144336(self):
        self._create_standard_items_ok()

        new_alias_path = "/deployments/local_vm/clusters/cluster1/configs/aliasconf"
        alias_name = "master1"
        self.model.create_item("alias-cluster-config", new_alias_path)
        alias_a1 = self.model.create_item("alias",
                                          new_alias_path + "/aliases/a1",
                                          address="11.11.11.1",
                                          alias_names=alias_name)
        alias_a1.set_initial()
        errors = self.plugin.validate_model(self.context)
        # No errors with a unique alias
        self.assertEquals([], errors)

        # ----

        alias_a2 = self.model.create_item("alias",
                                          new_alias_path + "/aliases/a2",
                                          address="12.12.12.1",
                                          alias_names=alias_name)
        alias_a2.set_initial()
        errors = self.plugin.validate_model(self.context)
        error = ValidationError(item_path="/deployments/local_vm/clusters/cluster1/nodes/node1",
                                property_name="alias_name",
                                error_message="Duplicate alias for master1 found at %s, %s" % (alias_a1.get_vpath(), alias_a2.get_vpath()))
        # An error is still expected with duplicate Initial aliases
        self.assertTrue(error in errors, )

        # ----
        alias_a2.alias_names = 'a-different-primary-alias,' + alias_name
        alias_a2.properties['alias_names'] = alias_a2.alias_names

        errors = self.plugin.validate_model(self.context)
        # No duplicates when the primary-alias is distinct
        self.assertEquals([], errors)

        alias_a2.set_applied()

        # ----

        alias_a2.set_for_removal()

        node4 = self._create_standard_4th_node_item()
        node4.set_initial()

        tasks = self.plugin.create_configuration(self.context)

        call_ids = defaultdict(list)
        for task in tasks:
            if task.model_item.item_type_id == 'node':
                call_ids[task.call_id].append("%s : %s" % (task.model_item.get_vpath(), task.description))

        for call_id, instances in call_ids.items():
            self.assertEquals(1, len(instances))

    def testValidateDuplicatesAtConfig(self):
        self._create_standard_items_ok()

        self.model.create_item(
            "alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1"
                "/configs/aliasconf")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master2",
            address="11.11.11.1", alias_names="master1")

        result = self.plugin.validate_model(self.context)
        self.assertEquals(ValidationError(
            item_path="/deployments/local_vm/clusters/cluster1/nodes/node1",
            property_name="alias_name",
            error_message='Duplicate alias for master1 found at '
                '/deployments/local_vm/clusters/cluster1'
                '/configs/aliasconf/aliases/master1, '
                '/deployments/local_vm/clusters/cluster1'
                '/configs/aliasconf/aliases/master2'), result[0])

    def testValidateDuplicatesTwoConfigs(self):
        self._create_standard_items_ok()

        self.model.create_item(
            "alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1"
                "/configs/aliasconf1")
        self.model.create_item(
            "alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1"
                "/configs/aliasconf2")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf1/aliases/master1",
            address="11.11.11.1", alias_names="master1")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf2/aliases/master2",
            address="11.11.11.1", alias_names="master1")
        item = self.model.get_item("/deployments/local_vm/clusters/cluster1"
                            "/configs/aliasconf2/aliases/master2")
        item.set_for_removal()

        result = self.plugin.validate_model(self.context)
        self.assertEquals(ValidationError(
            item_path="/deployments/local_vm/clusters/cluster1/nodes/node1",
            property_name="alias_name",
            error_message='Duplicate alias for master1 found at '
                '/deployments/local_vm/clusters/cluster1'
                '/configs/aliasconf1/aliases/master1, '
                '/deployments/local_vm/clusters/cluster1'
                '/configs/aliasconf2/aliases/master2'), result[0])

    def testGeneralValidation(self):
        self._create_standard_items_ok()

        result = self.model.create_item(
            "alias",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf1/aliases/master1",
            alias_names="master1",
            address="11.11.11.1")
        self.assertEquals(ValidationError(
             item_path="/deployments/local_vm/clusters/cluster1"
             "/nodes/node1/configs/aliasconf1/aliases/master1",
            error_message="Path not found",
            error_type=constants.INVALID_LOCATION_ERROR), result[0])

        self.model.create_item(
            "alias-node-config",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf")
        result = self.model.create_item(
            "alias",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf/aliases/master1",
            alias_names="master1")
        self.assertEquals(ValidationError(
            property_name="address",
            error_message='ItemType "alias" is required to have a '
                'property with name "address"',
            error_type=constants.MISSING_REQ_PROP_ERROR), result[0])
        result = self.model.create_item(
            "alias",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf/aliases/master2",
            address="11.11.11.1")
        self.assertEquals(ValidationError(
            property_name="alias_names",
            error_message='ItemType "alias" is required to have a '
                'property with name "alias_names"',
            error_type=constants.MISSING_REQ_PROP_ERROR), result[0])
        result = self.model.create_item(
            "alias-node-config",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf/aliases/master2",
            address="11.11.11.1",
            alias_names="master2")
        self.assertEquals(ValidationError(
            item_path="/deployments/local_vm/clusters/cluster1"\
                "/nodes/node1/configs/aliasconf/aliases",
            error_message="'alias-node-config' is not an allowed type "\
                "for collection of item type 'alias'",
            error_type=constants.INVALID_CHILD_TYPE_ERROR), result[0])
        result = self.model.create_item(
            "alias",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/aliasconf/aliases/master2",
            address="11.11.11",
            alias_names="master2",
            invalid_prop="invalid")
        self.assertEquals(ValidationError(
            property_name="invalid_prop",
            error_message='"invalid_prop" is not an allowed property of alias',
            error_type=constants.PROP_NOT_ALLOWED_ERROR), result[0])

    def testRemoval(self):
        self._create_standard_items_ok()

        i1 = self.model.create_item("alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf")
        i2 = self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf/aliases/master1",
            address="11.11.11.1", alias_names="master1")

        i1.set_applied()
        i2.set_applied()

        self.model.query_by_vpath(
            "/ms/network_interfaces/if0").set_applied()

        self.model.query_by_vpath(
            "/deployments/local_vm/clusters"
            "/cluster1/nodes/node1/network_interfaces/if0")\
                .set_applied()

        self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1/nodes/node2")
        self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1/nodes/node3")

        self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf")

        node1 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1")
        node1._model_item.set_applied()

        alias = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/configs"
            "/aliasconf/aliases/master1")

        self.plugin.validate_model(self.context)
        tasks = self.plugin.create_configuration(self.context)

        self.assertTrue(
           ConfigTask(node1, alias,
                'Remove "master1" alias from node "node1"',
                'hosts::hostentry',
                'cluster1_node1_master1',
                name="master1",
                ip="11.11.11.1",
                comment='Created by LITP. Please do not edit',
                ensure='absent',
            )
        in tasks)

    def testRemoval_duplicate_aliases(self):
        self._create_standard_items_ok()

        self.model.create_item("alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf1")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf1/aliases/master1",
            address="11.11.11.1", alias_names="master1")

        self.model.create_item("alias-cluster-config",
            "/deployments/local_vm/clusters/cluster1/configs/aliasconf2")
        self.model.create_item("alias",
            "/deployments/local_vm/clusters/cluster1"
            "/configs/aliasconf2/aliases/master2",
            address="11.11.11.10", alias_names="master1,master2,test2")


        errors = self.plugin.validate_model(self.context)
        self.assertEquals(ValidationError(
            item_path="/deployments/local_vm/clusters/cluster1/nodes/node1",
            property_name="alias_name",
            error_message='Duplicate alias for master1 found at '
                '/deployments/local_vm/clusters/cluster1'
                '/configs/aliasconf1/aliases/master1, '
                '/deployments/local_vm/clusters/cluster1'
                '/configs/aliasconf2/aliases/master2'), errors[0])

    def testNodeRemoval(self):
        self._create_standard_items_ok()

        ms1 = self.context.query_by_vpath("/ms")
        ms1._model_item.set_applied()
        ms1_if0 = self.context.query_by_vpath("/ms/network_interfaces/if0")
        ms1_if0._model_item.set_applied()

        node1 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1")
        node1._model_item.set_applied()
        node1_if0 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1/network_interfaces/if0")
        node1_if0._model_item.set_applied()

        node2 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node2")
        node2._model_item.set_for_removal()
        node2_if0 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node2/network_interfaces/if0")
        node2_if0._model_item.set_for_removal()

        node3 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node3")
        node3._model_item.set_applied()
        node3_if0 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node3/network_interfaces/if0")
        node3_if0._model_item.set_applied()

        self.plugin.validate_model(self.context)
        tasks = self.plugin.create_configuration(self.context)

        ms_task = ConfigTask(ms1, node2_if0,
            'Update node "{0}" host file removing node "node2" entry'.format(ms1.hostname),
            'hosts::hostentry',
            'node2',
            name="node2",
            ip="10.0.1.1",
            comment='Created by LITP. Please do not edit',
            ensure='absent',
        )
        ms_task.persist=False
        self.assertTrue(ms_task in tasks)
        node1_task = ConfigTask(node1, node2_if0,
                'Update node "node1" host file removing node "node2" entry',
                'hosts::hostentry',
                'node2',
                name="node2",
                ip="10.0.1.1",
                comment='Created by LITP. Please do not edit',
                ensure='absent',
        )
        node1_task.persist=False
        self.assertTrue(node1_task in tasks)
        node3_task = ConfigTask(node3, node2_if0,
                'Update node "node3" host file removing node "node2" entry',
                'hosts::hostentry',
                'node2',
                name="node2",
                ip="10.0.1.1",
                comment='Created by LITP. Please do not edit',
                ensure='absent',
        )
        node3_task.persist=False
        self.assertTrue(node3_task in tasks)

    def test_is_upgrade_flag_set_True(self):

        def mock_query(item_type):
            if item_type == 'node':
                node =  MagicMock()
                node.query = MagicMock(
                    return_value = [MagicMock(redeploy_ms='true')])
                return [node]

        api = MagicMock()
        api.query = mock_query
        result = self.plugin._is_upgrade_flag_set(api, 'redeploy_ms')
        self.assertTrue(result)

    def test_is_upgrade_flag_set_False(self):

        def mock_query(item_type):
            if item_type == 'node':
                node =  MagicMock()
                node.query = MagicMock(
                    return_value = [MagicMock(redeploy_ms='false')])
                return [node]

        api = MagicMock()
        api.query = mock_query
        result = self.plugin._is_upgrade_flag_set(api, 'redeploy_ms')
        self.assertFalse(result)

    @patch.object(HostsPlugin, '_is_upgrade_flag_set', Mock(return_value=True))
    def test_create_cfg_redeploy_ms(self):
        self._create_standard_items_ok()
        config_tasks = self.plugin.create_configuration(self.context)
        # TORF-619631 results in a new hostreplace task being generated first.
        self.assertEqual(5, len(config_tasks))
        self.assertTrue('host file with FQDN' in config_tasks[0].description)
        for task in config_tasks[1:5]:
            self.assertTrue("host file with node" in task.description)

    @patch.object(HostsPlugin, '_is_upgrade_flag_set', Mock(return_value=False))
    def test_create_cfg_with_multiple_clusters(self):
        self._create_standard_items_clusters_ok()
        config_tasks = self.plugin.create_configuration(self.context)
        self.assertEqual('hosts::replacehost', config_tasks[0].call_type)
        self.assertEqual('hosts::hostentry', config_tasks[1].call_type)
        self.assertEqual(26, len(config_tasks))

    @patch.object(HostsPlugin, '_is_upgrade_flag_set', Mock(return_value=True))
    def test_create_cfg_redeploy_ms_with_multiple_clusters(self):
        self._create_standard_items_clusters_ok()
        config_tasks = self.plugin.create_configuration(self.context)
        self.assertTrue('host file with FQDN' in config_tasks[0].description)
        for task in config_tasks[1:4]:
            self.assertTrue("host file with node" in task.description)

        self.assertEqual('hosts::hostentry', config_tasks[5].call_type)
        self.assertEqual('/ms/configs/aliasconf/aliases/master1',config_tasks[5].item_vpath)
        self.assertTrue("alias" in config_tasks[5].description) # its an alias
        self.assertEqual(6, len(config_tasks))

if __name__ == '__main__':
    unittest.main()
