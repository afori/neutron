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

"""database schema/model."""
import sqlalchemy as sa

from neutron.db import model_base
from neutron.db import models_v2
import neutron.db.api as db


class ML2_PN_Network(model_base.BASEV2, models_v2.HasId, models_v2.HasTenant):
    """Schema for network."""

    vlan = sa.Column(sa.String(10))
    segment_id = sa.Column(sa.String(36))
    network_type = sa.Column(sa.String(10))
    physical_network = sa.Column(sa.String(36))


class ML2_PN_Port(model_base.BASEV2, models_v2.HasId, models_v2.HasTenant):
    """Schema for port."""

    network_id = sa.Column(sa.String(36),
                           sa.ForeignKey("ml2_pn_networks.id"),
                           nullable=False)
    admin_state_up = sa.Column(sa.Boolean, nullable=False)
    host_id = sa.Column(sa.String(36))
    vlan_id = sa.Column(sa.String(36))

class ML2_PN_Device(model_base.BASEV2, models_v2.HasId,):
    """Schema for network device."""

    hostname = sa.Column(sa.String(36))
    status = sa.Column(sa.String(10))

def create_network(context, net_id, vlan, segment_id, network_type, tenant_id, physical_network):
    """Create a network"""

    # only network_type of vlan is supported
    session = context.session
    with session.begin(subtransactions=True):
        net = get_network(context, net_id, None)
        if not net:
            net = ML2_PN_Network(id=net_id, vlan=vlan,
                                     segment_id=segment_id,
                                     network_type='vlan',
                                     tenant_id=tenant_id,
                                     physical_network=physical_network)
            session.add(net)
    return net


def delete_network(context, net_id):
    """Delete a network"""

    session = context.session
    with session.begin(subtransactions=True):
        net = get_network(context, net_id, None)
        if net:
            session.delete(net)


def get_network(context, net_id, fields=None):
    """Get a network"""

    session = context.session
    return session.query(ML2_PN_Network).filter_by(id=net_id).first()


def get_networks():
    """Get all networks."""

    session = db.get_session()
    return session.query(ML2_PN_Network).all()


def create_port(context, port_id, network_id, host_id,
                vlan_id, tenant_id, admin_state_up):
    """Create a port"""

    session = context.session
    with session.begin(subtransactions=True):
        port = get_port(context, port_id)
        if not port:
            port = ML2_PN_Port(id=port_id,
                               network_id=network_id,
                               host_id=host_id,
                               vlan_id=vlan_id,
                               admin_state_up=admin_state_up,
                               tenant_id=tenant_id)
            session.add(port)

    return port


def get_port(context, port_id):
    """get a port"""

    session = context.session
    return session.query(ML2_PN_Port).filter_by(id=port_id).first()


def get_ports(network_id=None):
    """get a port"""

    session = db.get_session()
    return session.query(ML2_PN_Port).filter_by(network_id=network_id).all()


def delete_port(context, port_id):
    """delete port"""

    session = context.session
    with session.begin(subtransactions=True):
        port = get_port(context, port_id)
        if port:
            session.delete(port)


def update_port_state(context, port_id, admin_state_up):
    """Update port attributes"""

    session = context.session
    with session.begin(subtransactions=True):
        session.query(ML2_PN_Port).filter_by(id=port_id).update({'admin_state_up': admin_state_up})

