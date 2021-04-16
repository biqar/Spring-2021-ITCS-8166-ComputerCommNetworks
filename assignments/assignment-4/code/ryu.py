# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology import event
# Below is the library used for topo discovery
from ryu.topology.api import get_switch, get_link, get_host

import copy
import subprocess
import networkx as nx

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        # USed for learning switch functioning
        self.mac_to_port = {}
        self.bandwidth = {}
        # Holds the topology data and structure
        self.topo_raw_switches = []
        self.topo_raw_links = []
        self.topo_raw_hosts = {}
        # Maximum count to wait before printing the topology and measuring the link-costs
        self.MAX_COUNT = 300
        # Count to print topology data after convergence
        self.count = 0
        self.g = nx.DiGraph()
        self.host_locate = {'1': {'00:00:00:00:00:01'},
                            '2': {'00:00:00:00:00:02'},
                            '4': {'00:00:00:00:00:04'},
                            '5': {'00:00:00:00:00:05'},
                            '6': {'00:00:00:00:00:06'}
                            }
        self.topo = {'1': {'2': 10, '3': 10, '5': 15},
                     '2': {'1': 10, '3': 15, '4': 15},
                     '3': {'1': 10, '2': 15, '4': 5},
                     '4': {'2': 15, '3': 5, '6': 10},
                     '5': {'1': 15, '6': 15},
                     '6': {'5': 15, '4': 10}
                     }


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    # We are not using this function
    def delete_flow(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for dst in self.mac_to_port[datapath.id].keys():
            match = parser.OFPMatch(eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    """
    This is called when Ryu receives an OpenFlow packet_in message. The trick is set_ev_cls decorator. This decorator
    tells Ryu when the decorated function should be called.
    """
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # self.logger.info('  _packet_in_handler: src_mac -> %s' % eth.src)
        # self.logger.info('  _packet_in_handler: dst_mac -> %s' % eth.dst)
        # self.logger.info('  _packet_in_handler: %s' % pkt)
        # self.logger.info('  ------')

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        src_dpid = self.dpid_hostLookup(src)
        dst_dpid = self.dpid_hostLookup(dst)
        self.mac_to_port.setdefault(dpid, {})

        if dst_dpid is not None:
            self.logger.info("\n\tpacket in %s %s %s %s %s", dpid, src, dst, dst_dpid, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # self.print_topo();
        # build graph
        self.g.add_nodes_from([switch.dp.id for switch in self.topo_raw_switches])
        # run dijkstra to find path
        if str(src_dpid) in self.topo and str(dst_dpid) in self.topo:
            self.logger.info("calling to dijkstra with source %s destination %s", src_dpid, dst_dpid)
            path = self.dijkstra(str(src_dpid), str(dst_dpid))

        # todo: forward packets based on the Dijkstra's shortest path

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
        # print(type(get_host(self, None)))
        # self.topo_raw_hosts |= list(get_host(self, None))
        for host in list(get_host(self, None)):
            self.topo_raw_hosts[host.port.dpid] = host

    """
    Calculate shortest path tree from the src
    """
    def dijkstra(self, src, dest, visited=[], dist={}, parent={}):
        # sanity checks
        if src not in self.topo:
            raise TypeError('The root of the shortest path tree cannot be found')
        if dest not in self.topo:
            raise TypeError('The target of the shortest path cannot be found')

        # base condition
        if src == dest:
            # build the shortest path
            path = []
            p = dest
            while p is not None:
                path.append(p)
                p = parent.get(p, None)
            print('shortest path found: ' + str(path) + " with delay cost= " + str(dist[dest]))

            # clear the local variables
            dist.clear()
            parent.clear()
            del visited[:]
            return path

        else:
            # it will reach for the root-source vertex
            # initializing the cost with 0
            if len(visited) == 0:
                dist[src] = 0

            # visit the neighbors
            for neighbor in self.topo[src]:
                if neighbor not in visited:
                    new_distance = dist[src] + self.topo[src][neighbor]
                    if new_distance < dist.get(neighbor, float('inf')):
                        dist[neighbor] = new_distance
                        parent[neighbor] = src

            # mark the source as visited
            visited.append(src)

            # all neighbors distance have been updated
            # now select the non-visited node with lowest distance
            # and run Dijkstra sourcing from that lowest distance vertex
            unvisited = {}
            for k in self.topo:
                if k not in visited:
                    unvisited[k] = dist.get(k, float('inf'))
            if len(unvisited) > 0:
                next_vertex = min(unvisited, key=unvisited.get)
                return self.dijkstra(next_vertex, dest, visited, dist, parent)


    """
        Find dpid from mac address
    """
    def dpid_hostLookup(self, lmac):
        for dpid, mac in self.host_locate.iteritems():
            if lmac in mac:
                return dpid


    """
    The event EventLinkAdd will trigger the activation of handler_link_add().
    """
    @set_ev_cls(event.EventLinkAdd)
    def handler_link_add(self, ev):
        # The Function get_link(self, None) outputs the list of links.
        # del self.topo_raw_links[:]
        self.topo_raw_links = copy.copy(get_link(self, None))


    """
    The event EventSwitchEnter will trigger the activation of handler_switch_enter().
    """
    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev):
        # The Function get_switch(self, None) outputs the list of switches.
        # del self.topo_raw_switches[:]
        self.topo_raw_switches = copy.copy(get_switch(self, None))

    """
    Print saved topology data
    """
    def print_topo(self):
        print(" \t" + "Current Hosts:")
        for h in self.topo_raw_hosts.values():
            print(" \t\t" + str(h))

        print(" \t" + "Current Switches:")
        for s in self.topo_raw_switches:
            print(" \t\t" + str(s))

        print(" \t" + "Current Links:")
        for l in self.topo_raw_links:
            print(" \t\t" + str(l))
