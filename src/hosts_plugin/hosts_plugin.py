####################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
####################################################################

# Created: October 2013
# Authors: Team Dougal


from collections import defaultdict
from litp.core.execution_manager import ConfigTask
from litp.core.plugin import Plugin
from litp.core.litp_logging import LitpLogger
from litp.core.validators import ValidationError
from litp.core.translator import Translator
from litp.plan_types.deployment_plan import deployment_plan_tags

import re

t = Translator('ERIClitphosts_CXP9030589')
_ = t._


_log = LitpLogger()


def _all_aliasnames(alias):
    alias_names = alias.alias_names.split(',') if alias.alias_names else []
    return [name.strip() for name in alias_names]


def _aliasnames(alias):
    return _all_aliasnames(alias)[1:]


def _hostname(alias):
    return _all_aliasnames(alias)[0]


def _applied_all_aliasnames(alias):
    alias_names = alias.applied_properties['alias_names'].split(',') if \
        'alias_names' in alias.applied_properties else []
    return [name.strip() for name in alias_names]


def _applied_aliasnames(alias):
    return _applied_all_aliasnames(alias)[1:]


def _applied_hostname(alias):
    return _applied_all_aliasnames(alias)[0]


def _safe_applied_hostname(alias):
    try:
        return _applied_hostname(alias)
    except IndexError:
        return None


def _available_hostname(alias):
    try:
        return _applied_hostname(alias)
    except IndexError:
        return _hostname(alias)


class HostsPlugin(Plugin):
    """
    The Hosts Plugin class creates the configuration tasks required to
    configure /etc/hosts for all management network IP addresses.
    The plugin creates entries for the Management Server (MS) and all
    the Managed Nodes (MNs) in a cluster in the /etc/hosts file of the MS
    and in the /etc/hosts file of each of the the MNs. Update and remove
    reconfiguration actions are supported for this plugin.

    Service aliases for external network services are created so that the
    MNs and the MS can access these services. An alias is just an
    alternate name that can be used to make a connection. The alias
    encapsulates the required elements of a connection, and exposes them
    with a name chosen by the user.
    """

    RESTRICTED_ALIASES = ['localhost', 'localhost.localdomain', 'localhost',
            'localhost4', 'localhost4.localdomain4', 'local',
            'puppet', 'localhost6.localdomain6', 'localhost6']

    def __init__(self):
        self._aud_cache = {}

    def validate_model(self, api):
        '''
    * For a given cluster, no two host aliases can point at the same address
    * An alias config cannot be defined without first having an alias defined
    * Duplicate aliases (aliases with the same alias_name) are not allowed \
on nodes and clusters.
    * Node level aliases can not override the cluster level aliases
    * Certain aliases are restricted and cannot be used:

     * 'localhost.localdomain', 'localhost'
     * 'localhost4.localdomain4', 'localhost4'
     * 'localhost6.localdomain6', 'localhost6'
     * 'puppet'
     * Hostname of the MS
     * Hostnames already in use by nodes
    '''
        self._aud_cache.clear()
        errors = []

        clusters = api.query('cluster')
        mses = api.query('ms')
        all_nodes = api.query("node")

        for entity in mses + clusters:
            if entity.item_type_id == 'ms':
                entity_alias_items = entity.configs.query("alias")
                data = self._gen_alias_data(entity, entity_alias_items)
                errors.extend(self._gen_duplication_errors(data, api, entity))
            else:
                errors.extend(self._restricted_aliases(api,
                                                   entity.query("alias")))

                entity_alias_items = entity.configs.query("alias")

                for node in entity.nodes:
                    all_node_alias_items = (entity_alias_items +
                                            node.configs.query("alias"))

                    data = self._gen_alias_data(node, all_node_alias_items)
                    errors.extend(self._gen_duplication_errors(data,
                                                               api, node))

            alias_map = self._collect_aliases(entity.query("alias"))
            errors.extend(self._node_hostname_clashes(all_nodes, alias_map))

        return errors

    def _gen_duplication_errors(self, data, api, error_item):
        errors = []
        for alias_name, aliases in data.items():
            if len(aliases) > 1:
                duplicates = self._process_alias_data(aliases, api)
                if duplicates:
                    error = ValidationError(item_path=error_item.get_vpath(),
                       property_name="alias_name",
                       error_message=(_("DUPLICATE_ALIAS_FOR_X_FOUND_AT_VPATH")
                                      % (alias_name, ", ".join(duplicates))))
                    errors.append(error)
        return errors

    def _process_alias_data(self, alias_tuples, api):

        duplicates = defaultdict(list)

        def _aud(node, alias):
            if (node, alias) in self._aud_cache:
                return self._aud_cache[(node, alias)]
            else:
                aud = HostsPlugin._any_updated_duplicates(api, node, alias)
                self._aud_cache[(node, alias)] = aud
                return aud

        for (node, alias) in alias_tuples:
            primary_alias = None

            if ((alias.is_for_removal() and not node.is_initial() and
                 not _aud(node, alias))
                or
                (alias.is_updated() and not node.is_initial() and
                 _hostname(alias) != _safe_applied_hostname(alias))):
                primary_alias = _available_hostname(alias)

            if not alias.is_for_removal() or node.is_initial():
                primary_alias = _hostname(alias)

            if primary_alias:
                duplicates[primary_alias].append(alias.get_vpath())

        for dup_paths in duplicates.values():
            if len(dup_paths) > 1:
                return sorted(dup_paths)

    def _gen_alias_data(self, node, items):
        data = defaultdict(list)
        for item in items:
            for name in _all_aliasnames(item):
                data[name].append((node, item))
        return data

    def _node_hostname_clashes(self, nodes, alias_map):
        errors = []
        for node in nodes:
            if node.hostname in alias_map:
                map_name = alias_map[node.hostname][0].get_vpath()
                err_msg = (_("RESTRICTED_ALIAS_NAME_X_FOUND_AT_ALIAS_PATH") % (
                    node.hostname, map_name))
                errors.append(ValidationError(
                property_name="alias_names",
                error_message=err_msg))
        return errors

    def _restricted_aliases(self, api, aliases):
        errors = []
        restricted = [ms.hostname for ms in api.query('ms')]
        restricted.extend(HostsPlugin.RESTRICTED_ALIASES)
        for alias in aliases:
            for name in _all_aliasnames(alias):
                if name in restricted:
                    err_msg = (_("RESTRICTED_ALIAS_NAME_X_FOUND_AT_ALIAS_PATH")
                             % (name, alias.get_vpath()))
                    errors.append(ValidationError(property_name="alias_names",
                    error_message=err_msg))
        return errors

    def _collect_aliases(self, aliases):
        alias_map = dict()
        for alias in aliases:
            for name in _all_aliasnames(alias):
                if name not in alias_map:
                    alias_map[name] = []
                alias_map[name].append(alias)
        return alias_map

    def _collect_duplicates(self, alias_map, parent_item):
        errors = []
        for name, aliases in alias_map.items():
            if len(aliases) > 1:
                duplicates = sorted([item.get_vpath() for item in aliases])
                errors.append(ValidationError(
                    item_path=parent_item.get_vpath(),
                    property_name="alias_name",
                    error_message=(_("DUPLICATE_ALIAS_FOR_X_FOUND_AT_VPATH")
                         % (name, ", ".join(duplicates)))
                ))
        return errors

    def _collect_cluster_duplicates(self, api):
        errors = []
        for cluster in api.query("cluster"):
            seen_aliases = []
            cluster_configs = cluster.query("alias-cluster-config")
            for config in cluster_configs:
                aliases = config.query("alias")
                for alias in aliases:
                    hostnames = alias.alias_names.split(",")
                    for host in hostnames:
                        if host in seen_aliases:
                            errors.append(ValidationError(
                            item_path=config.get_vpath(),
                            property_name="alias_name",
                            error_message=(
                            _("DUPLICATE_ALIAS_VALUE_HOST_IN_CONFIG_ITEM_ID")
                                % (host, config.item_id))))
                        else:
                            seen_aliases.append(host)
        return errors

    def create_configuration(self, plugin_api_context):
        """
        Provides support for the addition of hosts entries in /etc/hosts file.
        Creating a deployment model of nodes will add all nodes on the
        management network to /etc/hosts files on all nodes including the MS.
        There is no additional CLI required, all information is gleaned from
        networking and host configuration data.
        When a management network IP address is updated the associated hosts
        entry in each /etc/hosts file will be updated also.

        **Creating a service alias**

        The following examples detail how to create service aliases:

        *Example CLI for creating a cluster level alias:*

        .. code-block:: bash

           litp create -t alias-cluster-config -p /deployments/local/clusters\
/c1/configs/alias_config

           litp create -t alias -p /deployments/local/clusters/c1/configs\
/alias_config/aliases/master_alias \
-o alias_names="master1" address="10.10.10.100"

        *Example CLI for a node level alias:*

        .. code-block:: bash

           litp create -t alias-node-config -p /deployments/local/clusters\
/c1/nodes/node1/configs/alias_config

           litp create -t alias -p /deployments/local/clusters/c1/nodes\
/node1/configs/alias_config/aliases/mysql_alias \
-o alias_names="mysql,queue" address="10.10.10.222"

        *Example XML for an alias:*

        .. code-block:: bash

            <?xml version='1.0' encoding='utf-8'?>
            <litp:alias xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xmlns:litp="http://www.ericsson.com/litp" xsi:schemaLocation=\
"http://www.ericsson.com/litp litp-xml-schema/litp.xsd" id="master_alias">
              <address>10.10.10.100</address>
              <alias_names>master1</alias_names>
              <name>master1</name>
            </litp:alias>

        For more information, see "Manage Service Aliases" \
from :ref:`LITP References <litp-references>`.

        """
        tasks = []
        nodes = []
        # Find all Peer Nodes and MS nodes
        lms_redeploy = HostsPlugin._is_upgrade_flag_set(
            plugin_api_context, 'redeploy_ms')
        nodes.extend([node for node in plugin_api_context.query('node')])
        mses = plugin_api_context.query('ms')

        mgt_net = None
        networks = plugin_api_context.query('network')
        for network in networks:
            # FIXME: Something seems a little unholy here..
            if network.litp_management == 'true':
                mgt_net = network.name
                break

        if mgt_net:
            _log.trace.debug("Using Management Network: " + mgt_net)
            HostsPlugin._add_node_entries(nodes, mses, tasks, mgt_net,
                                           lms_redeploy)
            tasks.extend(self._add_service_aliases(plugin_api_context,
                                                   lms_redeploy))

        return tasks

    def _add_service_aliases(self, api, lms_redeploy=False):
        tasks = []
        if not lms_redeploy:
            for cluster in api.query("cluster"):
                nodes = []
                for node in cluster.nodes:
                    if not node.is_for_removal() and not\
                                   node.is_removed():
                        nodes.append(node)
                tasks.extend(self._add_service_aliases_by_cluster(api, cluster,
                                                                   nodes))
        tasks.extend(self._add_service_aliases_by_node(api, lms_redeploy))
        return tasks

    def _add_service_aliases_by_cluster(self, api, cluster, nodes):
        tasks = []
        for alias_config in cluster.query("alias-cluster-config"):
            for alias in alias_config.aliases:
                for node in nodes:
                    tasks.extend(self._create_state_tasks(
                                         api, node, alias, cluster.item_id,
                                         model_items=(alias_config,)))
        return tasks

    def _add_service_aliases_by_node(self, api, lms_redeploy):
        tasks = []
        nodes = []
        if not lms_redeploy:
            nodes = [node for node in api.query('node')
                 if not node.is_for_removal() and not node.is_removed()]
        mses = api.query('ms')
        for node in nodes + mses:
            for alias_config in node.query("alias-node-config"):
                for alias in alias_config.aliases:
                    tasks.extend(self._create_state_tasks(api, node,
                        alias, "", model_items=(alias_config,)))
        return tasks

    def _create_state_tasks(self, api, node, alias, cluster_id,
            model_items=None):

        def available_aliasnames():
            """Return applied aliasnames otherwise return from properties"""
            result = _applied_aliasnames(alias)  # empty_list[1:] -> returns []
            if not result:
                return _aliasnames(alias)
            return result

        def available_property(item, name):
            """Return applied property otherwise return from properties"""
            return item.applied_properties.get(name, item.properties[name])

        def _aud(node, alias):
            if (node, alias) in self._aud_cache:
                return self._aud_cache[(node, alias)]
            else:
                aud = HostsPlugin._any_updated_duplicates(api, node, alias)
                self._aud_cache[(node, alias)] = aud
                return aud

        tasks = []
        if not node.is_initial() and alias.is_for_removal() and \
                not _aud(node, alias):
            tasks.append(HostsPlugin._create_alias_task(cluster_id, node,
                alias, _available_hostname(alias),
                available_aliasnames(),
                HostsPlugin._remove_ip_prefix(
                    available_property(alias, 'address')),
                'Remove "{0}" alias(es) from node "{1}"'.format(
                    ','.join(_all_aliasnames(alias)),
                    available_property(node, 'hostname')),
                ensure="absent"))
        if not node.is_initial() and alias.is_updated() and \
             _hostname(alias) != _safe_applied_hostname(alias):
            tasks.append(HostsPlugin._create_alias_task(cluster_id, node,
                alias, _available_hostname(alias),
                available_aliasnames(),
                HostsPlugin._remove_ip_prefix(
                    available_property(alias, 'address')),
                'Remove "{0}" alias from node "{1}"'.format(
                    _available_hostname(alias),
                    available_property(node, 'hostname')),
                ensure="absent"))
        if alias.is_initial() or alias.is_updated() or node.is_initial():
            tasks.append(HostsPlugin._create_alias_task(cluster_id, node,
                alias, _hostname(alias), _aliasnames(alias),
                HostsPlugin._remove_ip_prefix(alias.address),
                'Update node "%s" host file with "%s" alias(es)' % (
                    node.hostname, ','.join(_all_aliasnames(alias))),
                model_items=model_items))
        return tasks

    @staticmethod
    def _is_upgrade_flag_set(api_context, flag):
        """
        Check if a specific upgrade flag is set
        e.g redeploy_ms which will trigger
        the generation of MS based tasks only.
        ie. LMS Redeploy Plan for RH6 Plan in RH7 Uplift.
        :param api_context: Plugin API context
        :type api_context: class PluginApiContext
        :param flag: Upgrade flag
        :type flag: string
        :return: True if flag is set on an upgrade item , else False
        :rtype: boolean
        """
        if api_context and any(
            [True for node in api_context.query('node')
             for upgrd_item in node.query('upgrade')
             if getattr(upgrd_item, flag, 'false') == 'true']):
            _log.trace.info('Upgrade flag {0} is true.'.format(flag))
            return True
        else:
            return False

    @staticmethod
    def _any_updated_duplicates(api, source_node, source_alias):
        for cluster in api.query("cluster"):
            cluster_acc = cluster.query("alias-cluster-config")
            for node in cluster.nodes:
                for alias_config in cluster_acc:
                    for alias in alias_config.aliases:
                        if not alias.is_for_removal() and \
                                not alias.is_removed():
                            if alias.address == source_alias.address and \
                                source_node.hostname == node.hostname and \
                                _hostname(alias) == _hostname(source_alias):
                                return True
        return False

    @staticmethod
    def _create_alias_task(cluster_id, node, alias, hostname, alias_names,
            address, message, ensure="present", model_items=None):
        call_id = "%s_%s_%s" % (cluster_id, node.hostname, hostname)
        task = ConfigTask(node,
            alias,
            message,
            'hosts::hostentry',
            call_id,
            name=hostname,
            ip=address,
            comment='Created by LITP. Please do not edit',
            ensure=ensure)

        #TORF-113300 Even an empty array is valid and if empty will remove
        #the host names from the host_aliases list in the manifest file
        if alias_names or (alias.is_updated() and _applied_aliasnames(alias)):
            task.kwargs['host_aliases'] = alias_names

        if model_items:
            task.model_items.update(model_items)
        return task

    @staticmethod
    def _get_values(name, ip_addr, ensure='present'):
        return {'name': name,
                'ip': ip_addr,
                'comment': 'Created by LITP. Please do not edit',
                'ensure': ensure}

    @staticmethod
    def _create_task(update_node, entry_node, ipaddr, iface):
        task = ConfigTask(update_node, iface,
                  'Update node "%s" host file with node "%s" entry' %\
                        (update_node.hostname, entry_node.hostname),
                  'hosts::hostentry',
                  entry_node.hostname,
                  **(HostsPlugin._get_values(entry_node.hostname, ipaddr)))
        return task

    @staticmethod
    def _create_fqdn_task(node, iface):
        fqdn = None
        if node.domain is not None:
            fqdn = node.hostname + "." + node.domain + "\t" + node.hostname
        else:
            if node.item_type_id == 'ms':
                fqdn = node.hostname
            else:
                fqdn = ""

        task = ConfigTask(node, iface,
                        'Update node "%s" host file with FQDN' % node.hostname,
                        'hosts::replacehost',
                        node.hostname,
                        fqdn=fqdn)
        return task

    @staticmethod
    def _remove_task(update_node, entry_node, ipaddr, iface):
        task = ConfigTask(update_node, iface,
                  'Update node "%s" host file removing node "%s" entry' %\
                        (update_node.hostname, entry_node.hostname),
                  'hosts::hostentry',
                  entry_node.hostname,
        **(HostsPlugin._get_values(entry_node.hostname, ipaddr, 'absent')))
        task.persist = False
        return task

    @staticmethod
    def _ip_has_changed(iface):
        return iface.is_updated() and \
            iface.applied_properties.get('ipaddress') != iface.ipaddress

    @staticmethod
    def _should_update_hosts_file(node, network_name):
        for iface in node.network_interfaces:
            # LITPCDS-10035
            # If the model item is in a "dirty" state, we need to create the
            # task anyway ...
            if (hasattr(iface, 'network_name') and \
                iface.network_name == network_name) and \
               (HostsPlugin._ip_has_changed(iface) or \
                not iface.applied_properties_determinable):
                return True
            # network name may have been removed
            elif HostsPlugin._ip_has_changed(iface):
                return HostsPlugin._has_moved_updated_ipaddr(node,
                                                             iface,
                                                             network_name)
        return False

    @staticmethod
    def _has_moved_updated_ipaddr(node, interface, mgt_net):
        # Find the iface with the address
        _log.trace.debug("has_moved_updated_ipaddr")
        mgt_ifaces = [iface for iface in node.network_interfaces
                   if hasattr(iface, 'network_name') and
                      iface.network_name == mgt_net and
                      hasattr(iface, 'ipaddress')]
        if mgt_ifaces:
            mgt_iface = mgt_ifaces[0]
            _log.trace.debug("iface.item_id is %s" % mgt_iface.item_id)
            if mgt_iface.ipaddress != \
               interface.applied_properties.get('ipaddress'):
                return True
        return False

    @staticmethod
    def _remove_ip_prefix(ipaddr):
        return re.sub(r'\/\d+$', '', ipaddr)

    @staticmethod
    def _get_mgmt_iface(node, mgt_net):
        for iface in node.network_interfaces:
            if iface.network_name == mgt_net:
                return (iface.ipaddress, iface)
        return (None, None)

    @staticmethod
    def _add_node_entries(nodes, mses, tasks, mgt_net, redeploy_ms):
        all_nodes = nodes + mses
        nodes_for_tasks = mses
        if not redeploy_ms:
            nodes_for_tasks.extend(nodes)
        #change_all ensures existing nodes are added to a new node's host file
        for current_node in nodes_for_tasks:
            change_all = False
            if current_node.is_initial():
                change_all = True

            if hasattr(current_node, 'domain') \
                    and (change_all or
                         (current_node.is_updated() and current_node.domain !=\
                          current_node.applied_properties.get('domain'))):
                (_, mgt_iface) = HostsPlugin._get_mgmt_iface(current_node,
                                                             mgt_net)
                if mgt_iface:
                    _log.trace.debug("Updating loopback host entry to include"
                                     " FQDN for %s" % current_node.hostname)
                    task = HostsPlugin._create_fqdn_task(current_node,
                                                         mgt_iface)
                    if task:
                        tasks.append(task)

            for node in all_nodes:
                if node.is_initial() or change_all or \
                   HostsPlugin._should_update_hosts_file(node, mgt_net) or \
                   node.is_for_removal():
                    task = HostsPlugin._add_host_task(current_node,
                                                      node,
                                                      mgt_net)
                    if task:
                        tasks.append(task)

    @staticmethod
    def _add_host_task(target_node, entry_node, mgt_net):
        _log.trace.debug("entry_node.item_id is %s" % entry_node.item_id)
        mgmt_ip = None
        mgmt_iface = None
        node_task = None

        (mgmt_ip, mgmt_iface) = HostsPlugin._get_mgmt_iface(entry_node,
                                                            mgt_net)

        if mgmt_ip:
            _log.trace.debug("ipaddr is %s" % mgmt_ip)
            if entry_node.is_for_removal():
                node_task = HostsPlugin._remove_task(
                    target_node,
                    entry_node,
                    mgmt_ip,
                    mgmt_iface)
            else:
                node_task = HostsPlugin._create_task(
                    target_node,
                    entry_node,
                    mgmt_ip,
                    mgmt_iface)
            if mgmt_iface.is_updated() and not target_node.is_initial():
                node_task.tag_name = deployment_plan_tags.MS_TAG

        return node_task
