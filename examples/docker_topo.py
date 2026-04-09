#!/usr/bin/python3

"""
Simple example of using docker nodes (host and switch)
"""

import argparse

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.nodelib import DockerNode
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.clean import cleanup


class SingleSwitchTopo(Topo):
    "Single switch connected to n (< 256) hosts."
    def __init__(self, n, **opts):
        """init function to setup the topology."""
        Topo.__init__(self, **opts)

        switch = self.addSwitch('s1', **opts.get("switch_opts", {}))

        for h in range(1, n+1):
            host = self.addHost('h%d' % h,
                                **opts.get("host_opts", {}),
                                )
            self.addLink(host, switch)

def main(num_hosts):
    """Main function."""
    topo = SingleSwitchTopo(
        num_hosts,
        switch_opts={"image": "alpine:latest"},
        host_opts={"image": "alpine:latest"},
    )
    net = Mininet(topo = topo,
                  host = DockerNode,
                  switch = DockerNode,
                  controller = None )
    net.start()
    CLI( net )
    net.stop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mininet demo')
    parser.add_argument('--num-hosts',
                        help='Number of hosts to connect to switch',
                        type=int, action="store", default=2)
    args = parser.parse_args()

    cleanup()
    setLogLevel( 'info' )
    main(args.num_hosts)
