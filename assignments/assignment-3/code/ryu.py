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
        self.topo_raw_hosts = []
        # Count to print topology data after convergence
        self.MAX_COUNT = 300
        self.count = 0


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

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("\tpacket in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

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

        self.topo_raw_hosts = []
        self.topo_raw_hosts = copy.copy(get_host(self, None))
        self.count = self.count + 1
        if self.count%self.MAX_COUNT == 0:
            # x = []
            self.print_topo()
            # for h in self.topo_raw_hosts:
            #     for ip in h.ipv4:
            #         host = 'h' + ip.split('.')[3]
            #         x.append(host)
            # print(x)
            print("***Measuring Bandwidth***")
            self.measure_bandwidth()
            print("Link Costs: {}".format(self.bandwidth))

    """
    Measure the bandwidth between hosts by using iperf
    """
    def measure_bandwidth(self):
        for s_host in self.topo_raw_hosts:
            s = s_host.port.dpid
            # s = 1
            hs = 'h' + str(s)
            # hs = 'h1' + str(s)
            hs_ip = '10.0.0.' + str(s)
            # s_result = subprocess.Popen(['/home/mininet/mininet/util/m', hs, 'iperf', '-s &> server.log &'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            # s_result = subprocess.call(['/home/mininet/mininet/util/m', hs, 'iperf', '-s'], shell=True)
            # server_log = str(s_result.communicate(input="mininet"))
            #s_result.rstrip()
            #print("iperf server log: {}".format(server_log))
            for c_host in self.topo_raw_hosts:
                c = c_host.port.dpid
                # condition to check whether client and server are the same host
                if c == s:
                    continue
                hc = 'h' + str(c)
                print("iperf --server on {} with ip {} and iperf --client in {}".format(hs, hs_ip, hc))
                # c_result = subprocess.Popen(['/home/mininet/mininet/util/m', hc, 'iperf', '-t 5', '-c', hs_ip, ' &> client.log &'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                c_result = subprocess.Popen(['/home/mininet/mininet/util/m', hc, 'iperf', '-t 5', '-c', hs_ip], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                # c_result = subprocess.call(['/home/mininet/mininet/util/m', hc, 'iperf', '-t 5', '-c', hs_ip])
                client_log = str(c_result.communicate())
                # client_log = str(c_result)
                # print("iperf client log: {}".format(client_log))
                bw = client_log
                bw = bw.split("Mbits/sec")[0]
                bw = bw.rstrip().split(" ")[-1]
                # print("bandwidth: {}".format(bw))
                self.bandwidth[(hc, hs)] = float(bw)
                # break
            # break


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
        for h in self.topo_raw_hosts:
            print(" \t\t" + str(h))

        print(" \t" + "Current Switches:")
        for s in self.topo_raw_switches:
            print(" \t\t" + str(s))

        print(" \t" + "Current Links:")
        for l in self.topo_raw_links:
            print(" \t\t" + str(l))

    # @set_ev_cls(event.EventSwitchEnter)
    # def get_topology_data(self, ev):
    #     switch_list = get_switch(self.topology_api_app, None)
    #     switches = [switch.dp.id for switch in switch_list]
    #     links_list = get_link(self.topology_api_app, None)
    #     links = [(link.src.dpid, link.dst.dpid, {'port': link.src.port_no}) for link in links_list]
    #     print("links: ".format(links))
    #     print("switches: ".format(switches))
