#!/usr/bin/python

from mininet.topo import Topo
from mininet.node import Controller
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel, info

class MyTopo(Topo):
    "Simple topology example."

    def __init__(self):
        "Create custom topo."

        # Initialize topology
        Topo.__init__(self)

        # Add hosts and switches
        h1 = [self.addHost('h1', ip='10.0.0.1/24')]
        h2 = [self.addHost('h2', ip='10.0.0.2/24')]
        h3 = [self.addHost('h3', ip='10.0.0.3/24')]
        h4 = [self.addHost('h4', ip='10.0.0.4/24')]
        h5 = [self.addHost('h5', ip='10.0.0.5/24')]
        h6 = [self.addHost('h6', ip='10.0.0.6/24')]

        s1 = [self.addSwitch('s1')]
        s2 = [self.addSwitch('s2')]
        s3 = [self.addSwitch('s3')]
        s4 = [self.addSwitch('s4')]
        s5 = [self.addSwitch('s5')]
        s6 = [self.addSwitch('s6')]

        # host to switch links
        self.addLink('s1', 'h1')
        self.addLink('s2', 'h2')
        self.addLink('s3', 'h3')
        self.addLink('s4', 'h4')
        self.addLink('s5', 'h5')
        self.addLink('s6', 'h6')

        # switch to switch links
        self.addLink('s1', 's2', cls=TCLink, bw=10)
        self.addLink('s1', 's3', cls=TCLink, bw=10)
        self.addLink('s1', 's5', cls=TCLink, bw=5)
        self.addLink('s3', 's4', cls=TCLink, bw=5)
        self.addLink('s5', 's6', cls=TCLink, bw=5)


def customTopo():
    "Create a network with custom topology and remote-controller"
    c0 = RemoteController('c0', ip='127.0.0.1', port=6633)  # external controller
    topo = MyTopo()
    net = Mininet(topo=topo, controller=c0)
    info("***Starting Network***\n")
    net.start()

    info("***Running CLI***\n")
    CLI(net)

    # print("Dumping host connections")
    # dumpNodeConnections(net.hosts)

    info("***Stopping Network***\n")
    net.stop()


if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    customTopo()
