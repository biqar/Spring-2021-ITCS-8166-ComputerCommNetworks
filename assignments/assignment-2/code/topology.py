#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel


class MyTopo(Topo):
    "Simple topology example."

    def __init__(self):
        "Create custom topo."

        # Initialize topology
        Topo.__init__(self)

        # Add hosts and switches
        h1 = [self.addHost('h1', ip='10.0.1.10/24')]
        h2 = [self.addHost('h2', ip='10.0.1.11/24')]
        h3 = [self.addHost('h3', ip='10.0.1.12/24')]
        h4 = [self.addHost('h4', ip='10.0.1.13/24')]
        h5 = [self.addHost('h5', ip='10.0.2.10/24')]
        h6 = [self.addHost('h6', ip='10.0.2.11/24')]
        h7 = [self.addHost('h7', ip='10.0.2.12/24')]
        h8 = [self.addHost('h8', ip='10.0.2.13/24')]
        h9 = [self.addHost('h9', ip='10.0.1.1/24')]
        h10 = [self.addHost('h10', ip='10.0.2.1/24')]

        s9 = [self.addSwitch('s9')]
        s10 = [self.addSwitch('s10')]
        s11 = [self.addSwitch('s11')]
        s12 = [self.addSwitch('s12')]
        s13 = [self.addSwitch('s13')]
        s14 = [self.addSwitch('s14')]
        s15 = [self.addSwitch('s15')]

        # host to switch links
        self.addLink('s11', 'h1')
        self.addLink('s11', 'h2')
        self.addLink('s12', 'h3')
        self.addLink('s12', 'h4')
        self.addLink('s14', 'h5')
        self.addLink('s14', 'h6')
        self.addLink('s15', 'h7')
        self.addLink('s15', 'h8')
        self.addLink('s9', 'h9')
        self.addLink('s9', 'h10')

        # switch to switch links
        self.addLink('s10', 's11')
        self.addLink('s10', 's12')
        self.addLink('s13', 's14')
        self.addLink('s13', 's15')
        self.addLink('s9', 's10')
        self.addLink('s9', 's13')


class MultiSwitchTopo(Topo):
    "Single switch connected to n hosts."

    def build(self, n=2):
        switch = self.addSwitch('s1')
        # Python's range(N) generates 0..N-1
        for h in range(n):
            host = self.addHost('h%s' % (h + 1))
            self.addLink(host, switch)


def simpleTest():
    "Create and test a simple network"
    topo = MultiSwitchTopo(n=4)
    net = Mininet(topo)
    net.start()
    print("Dumping host connections")
    dumpNodeConnections(net.hosts)
    print("Testing network connectivity")
    net.pingAll()
    net.stop()


if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    simpleTest()
