# Copyright 2014 Allied Telesis, inc
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""Implentation of Py-Networking Mechanism driver for ML2 Plugin."""

from oslo.config import cfg

from neutron.openstack.common import importutils
from neutron.openstack.common import log as logging
from neutron.plugins.ml2 import driver_api as api
from pprint import pprint
from pynetworking import Device
from neutron.plugins.ml2.drivers.pynetworking import db
import sys

LOG = logging.getLogger(__name__)
MECHANISM_VERSION = 0.0

class PyNetworkingMechanism(api.MechanismDriver):
    def initialize(self):
        LOG.debug(_("initialized: called"))

        # Read configuration
        LOG.info("Reading configurations files: {0}".format(', '.join(cfg.CONF.config_file)))
        multi_parser = cfg.MultiConfigParser()
        read_ok = multi_parser.read(cfg.CONF.config_file)

        if len(read_ok) != len(cfg.CONF.config_file):
            raise cfg.Error(_("Some config files were not parsed properly"))
	
	self._config = {}
        for parsed_file in multi_parser.parsed:
            for parsed_item in parsed_file.keys():
                dev_id, sep, dev_ip = parsed_item.partition(':')
                if dev_id.lower() == 'ml2_pynetworking':
                    for dev_key, value in parsed_file[parsed_item].items():
                        if dev_ip in self._config:
                            self._config[dev_ip][dev_key] = value[0]
                        else:
                            self._config[dev_ip] = { dev_key: value[0]}
        LOG.info("configuration: {0}".format(self._config))
        self._syncronize()

    def create_network_precommit(self, mech_context):
        LOG.debug(_("create_network_precommit: called"))

        network = mech_context.current
        context = mech_context._plugin_context
        tenant_id = network['tenant_id']
        network_id = network['id']

        segments = mech_context.network_segments
        # currently supports only one segment per network
        segment = segments[0]

        network_type = segment['network_type']
        vlan_id = segment['segmentation_id']
        segment_id = segment['id']
        physical_network = segment['physical_network']

        if network_type != 'vlan':
            raise Exception(
                _("failed to create network, "
                  "only network type vlan is supported"))

        try:
            db.create_network(context, network_id, vlan_id,
                              segment_id, network_type, tenant_id, physical_network)
        except Exception:
            LOG.exception(
                _("failed to create network in db"))
            raise Exception(
                _("create_network_precommit failed"))

        LOG.info(_("create network (precommit): %(network_id)s "
                   "of network type = %(network_type)s "
                   "with vlan = %(vlan_id)s "
                   "for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'network_type': network_type,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})

    def create_network_postcommit(self, mech_context):
        LOG.debug(_("create_network_postcommit: called"))

        network = mech_context.current
        context = mech_context._plugin_context

        network_id = network['id']
        network = db.get_network(context, network_id)
        network_type = network['network_type']
        tenant_id = network['tenant_id']
        vlan_id = network['vlan']

	for host, d in self._config.iteritems():
            try:
                dev = Device(host = host, username = d.get('username','manager'), password = d.get('password','friend'))
                dev.open()
                dev.vlan.create(vlan_id)
                dev.close()
                LOG.info("Vlan {0} created on the device {1}".format(vlan_id, host))
            except Exception:
                LOG.info("failed to create vlan on {0} ({1})".format(host, format(sys.exc_info()[0])))

        LOG.info(_("created network (postcommit): %(network_id)s"
                   " of network type = %(network_type)s"
                   " with vlan = %(vlan_id)s"
                   " for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'network_type': network_type,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})

    def delete_network_precommit(self, mech_context):
        LOG.debug(_("delete_network_precommit: called"))

        network = mech_context.current
        network_id = network['id']
        vlan_id = network['provider:segmentation_id']
        tenant_id = network['tenant_id']

        context = mech_context._plugin_context

        try:
            db.delete_network(context, network_id)
        except Exception:
            LOG.exception(_("failed to delete network in db"))
            raise Exception(_("delete_network_precommit failed"))

        LOG.info(_("delete network (precommit): %(network_id)s"
                   " with vlan = %(vlan_id)s"
                   " for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})

    def delete_network_postcommit(self, mech_context):
        LOG.debug(_("delete_network_postcommit: called"))

        network = mech_context.current
        network_id = network['id']
        vlan_id = network['provider:segmentation_id']
        tenant_id = network['tenant_id']

        for host, d in self._config.iteritems():
            try:
                dev = Device(host = host, username = d.get('username','manager'), password = d.get('password','friend'))
                dev.open()
                dev.vlan.delete(vlan_id)
                dev.close()
                LOG.info("Vlan {0} deleted on the device {1}".format(vlan_id, host))
            except Exception:
                LOG.info("failed to delete vlan on {0} ({1})".format(host, format(sys.exc_info()[0])))

        LOG.info(_("delete network (postcommit): %(network_id)s"
                   " with vlan = %(vlan_id)s"
                   " for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})

    def update_network_precommit(self, mech_context):
        LOG.info(_("update_network_precommit: called"))

    def update_network_postcommit(self, mech_context):
        LOG.info(_("update_network_postcommit: called"))

    def create_port_precommit(self, mech_context):
        LOG.info(_("create_port_precommit: called"))

        port = mech_context.current
        LOG.info(port)
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        host_id = port['binding:host_id']
        admin_state_up = port['admin_state_up']

        context = mech_context._plugin_context

        network = db.get_network(context, network_id)
        vlan_id = network['vlan']
        LOG.info(network)

        try:
            db.create_port(context, port_id, network_id, host_id,
                           vlan_id, tenant_id, admin_state_up)
        except Exception:
            LOG.exception(_("failed to create port in db"))
            raise Exception(_("create_port_precommit failed"))

    def create_port_postcommit(self, mech_context):
        LOG.info(_("create_port_postcommit: called"))

        port = mech_context.current
        context = mech_context._plugin_context

        port_id = port['id']
        port = db.get_port(context, port_id)
        LOG.info(port)
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        host_id = port['host_id']

        network = db.get_network(context, network_id)
        vlan_id = network['vlan']

        for host, d in self._config.iteritems():
            if network['physical_network'] in d['physical_networks'] and host_id in d: 
                try:
                    dev = Device(host = host, username = d.get('username','manager'), password = d.get('password','friend'))
                    dev.open()
                    dev.vlan.add_interface(vlan_id, d[host_id], tagged=True)
                    dev.close()
                    LOG.info("port {0} added to vlan {1}".format(d[host_id], vlan_id))
                except Exception:
                    LOG.exception("failed to delete port {2} form vlan on {0} ({1})".format(host, format(sys.exc_info()[0], d[host_id])))

        LOG.info(
            _("created port (postcommit): port_id=%(port_id)s"
              " network_id=%(network_id)s tenant_id=%(tenant_id)s"),
            {'port_id': port_id,
             'network_id': network_id, 'tenant_id': tenant_id})

    def delete_port_precommit(self, mech_context):
        LOG.info(_("delete_port_precommit: called"))

        port = mech_context.current
        LOG.info(port)
        port_id = port['id']

        context = mech_context._plugin_context

        try:
            db.delete_port(context, port_id)
        except Exception:
            LOG.exception(_("failed to delete port in db"))
            raise Exception(_("delete_port_precommit failed"))

    def delete_port_postcommit(self, mech_context):
        LOG.info(_("delete_port_postcommit: called"))

        port = mech_context.current
        LOG.info(port)
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        host_id = port['binding:host_id']

        context = mech_context._plugin_context

        network = db.get_network(context, network_id)
        vlan_id = network['vlan']

        for host, d in self._config.iteritems():
            if network['physical_network'] in d['physical_networks'] and host_id in d: 
                try:
                     dev = Device(host = host, username = d.get('username','manager'), password = d.get('password','friend'))
                     dev.open()
                     dev.vlan.delete_interface(vlan_id, d[host_id])
                     dev.close()
                     LOG.info("port {0} deleted from vlan {1}".format(d[host_id], vlan_id))
                except Exception:
                     LOG.exception(_("failed to delete port from vlan "))
                     raise Exception(_("delete_port_postcommit failed"))

        LOG.info(
            _("delete port (postcommit): port_id=%(port_id)s"
              " network_id=%(network_id)s tenant_id=%(tenant_id)s"),
            {'port_id': port_id,
             'network_id': network_id, 'tenant_id': tenant_id})

    def update_port_precommit(self, mech_context):
        LOG.info(_("update_port_precommit(self: called"))
        port = mech_context.current
        LOG.info(port)

    def update_port_postcommit(self, mech_context):
        LOG.info(_("update_port_postcommit: called"))
        port = mech_context.current
        LOG.info(port)

    def create_subnet_precommit(self, mech_context):
        LOG.debug(_("create_subnetwork_precommit: called"))
        pprint(mech_context.current)

    def create_subnet_postcommit(self, mech_context):
        LOG.debug(_("create_subnetwork_postcommit: called"))
        pprint(mech_context.current)

    def delete_subnet_precommit(self, mech_context):
        LOG.debug(_("delete_subnetwork_precommit: called"))
        pprint(mech_context.current)

    def delete_subnet_postcommit(self, mech_context):
        LOG.debug(_("delete_subnetwork_postcommit: called"))
        pprint(mech_context.current)

    def update_subnet_precommit(self, mech_context):
        LOG.debug(_("update_subnet_precommit(self: called"))
        pprint(mech_context.current)

    def update_subnet_postcommit(self, mech_context):
        LOG.debug(_("update_subnet_postcommit: called"))
        pprint(mech_context.current)

    def _syncronize(self):
        LOG.info(_("_syncronize: called"))

	# syncro networks
        for network in db.get_networks():
            LOG.info(network)
            for device, devinfo in self._config.iteritems():
                if network['physical_network'] in devinfo.get('physical_networks',''):
                    try:
                        d = Device(host = device, username = devinfo.get('username','manager'), password = devinfo.get('password','friend'))
                        d.open()
                        if network['vlan'] not in d.vlan:
                            d.vlan.create(network['vlan'])
                            LOG.info("Vlan {0} created on the device {1}".format(network['vlan'], device))

                        # syncro ports
                        for port in db.get_ports(network['id']):
                            LOG.info(port)
                            if port['host_id'] in devinfo and devinfo[port['host_id']] not in d.vlan[network['vlan']]['untagged']:
                                d.vlan.add_interface(network['vlan'], devinfo[port['host_id']], tagged=True)
                                LOG.info("port {0} added to vlan {1}".format(devinfo[port['host_id']], network['vlan']))
                        d.close()
                    except Exception:
                        LOG.info("failed to update device {0} ({1})".format(device, format(sys.exc_info()[0]), network['vlan']))


         
