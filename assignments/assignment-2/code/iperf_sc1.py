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
        self.addLink('s10', 's12', bw=15, delay='10ms')
        self.addLink('s13', 's14')
        self.addLink('s13', 's15')
        self.addLink('s9', 's10', bw=10)
        self.addLink('s9', 's13')


def perfTest():
    "Create network and run simple performance test"
    topo = MyTopo()
    net = Mininet(topo)
    net.start()
    print("Dumping host connections")
    dumpNodeConnections(net.hosts)

    print("Testing network connectivity")
    net.pingAll()

    for h in net.hosts:
        print("Testing bandwidth between {} and h9".format(h))
        h_, h9 = net.get(h, 'h9')
        net.iperf((h_, h9))

    print("Testing bandwidth between h1 and h9")
    h1, h9 = net.get('h1', 'h9')
    net.iperf((h1, h9))

    print("Testing bandwidth between h2 and h9")
    h2, h9 = net.get('h2', 'h9')
    net.iperf((h2, h9))

    print("Testing bandwidth between h3 and h9")
    h3, h9 = net.get('h3', 'h9')
    net.iperf((h3, h9))

    print("Testing bandwidth between h4 and h9")
    h4, h9 = net.get('h4', 'h9')
    net.iperf((h4, h9))

    print("Testing bandwidth between h5 and h9")
    h5, h9 = net.get('h5', 'h9')
    net.iperf((h5, h9))

    print("Testing bandwidth between h6 and h9")
    h6, h9 = net.get('h6', 'h9')
    net.iperf((h6, h9))

    print("Testing bandwidth between h7 and h9")
    h7, h9 = net.get('h7', 'h9')
    net.iperf((h7, h9))

    print("Testing bandwidth between h8 and h9")
    h8, h9 = net.get('h8', 'h9')
    net.iperf((h8, h9))

    print("Testing bandwidth between h9 and h9")
    h9, h9 = net.get('h9', 'h9')
    net.iperf((h9, h9))

    print("Testing bandwidth between h10 and h9")
    h10, h9 = net.get('h10', 'h9')
    net.iperf((h10, h9))

    net.stop()


if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    perfTest()
