"""
Node Library for Mininet

This contains additional Node types which you may find to be useful.
"""

import os
import pty
import re
import select
import subprocess
import time

from mininet.clean import addCleanupCallback
from mininet.node import Node, Host, Switch
from mininet.log import info, warn
from mininet.moduledeps import pathCheck
from mininet.util import isShellBuiltin, quietRun


class LinuxBridge( Switch ):
    "Linux Bridge (with optional spanning tree)"

    nextPrio = 100  # next bridge priority for spanning tree

    def __init__( self, name, stp=False, prio=None, **kwargs ):
        """stp: use spanning tree protocol? (default False)
           prio: optional explicit bridge priority for STP"""
        self.stp = stp
        if prio:
            self.prio = prio
        else:
            self.prio = LinuxBridge.nextPrio
            LinuxBridge.nextPrio += 1
        Switch.__init__( self, name, **kwargs )

    def connected( self ):
        "Are we forwarding yet?"
        if self.stp:
            return 'forwarding' in self.cmd( 'brctl showstp', self )
        else:
            return True

    def start( self, _controllers ):
        "Start Linux bridge"
        self.cmd( 'ifconfig', self, 'down' )
        self.cmd( 'brctl delbr', self )
        self.cmd( 'brctl addbr', self )
        if self.stp:
            self.cmd( 'brctl setbridgeprio', self.prio )
            self.cmd( 'brctl stp', self, 'on' )
        for i in self.intfList():
            if self.name in i.name:
                self.cmd( 'brctl addif', self, i )
        self.cmd( 'ifconfig', self, 'up' )

    def stop( self, deleteIntfs=True ):
        """Stop Linux bridge
           deleteIntfs: delete interfaces? (True)"""
        self.cmd( 'ifconfig', self, 'down' )
        self.cmd( 'brctl delbr', self )
        super( LinuxBridge, self ).stop( deleteIntfs )

    def dpctl( self, *args ):
        "Run brctl command"
        return self.cmd( 'brctl', *args )

    @classmethod
    def setup( cls ):
        "Check dependencies and warn about firewalling"
        pathCheck( 'brctl', moduleName='bridge-utils' )
        # Disable Linux bridge firewalling so that traffic can flow!
        for table in 'arp', 'ip', 'ip6':
            cmd = 'sysctl net.bridge.bridge-nf-call-%stables' % table
            out = quietRun( cmd ).strip()
            if out.endswith( '1' ):
                warn( 'Warning: Linux bridge may not work with', out, '\n' )


class NAT( Node ):
    "NAT: Provides connectivity to external network"

    def __init__( self, name, subnet='10.0/8',
                  localIntf=None, flush=False, **params):
        """Start NAT/forwarding between Mininet and external network
           subnet: Mininet subnet (default 10.0/8)
           flush: flush iptables before installing NAT rules"""
        super( NAT, self ).__init__( name, **params )

        self.subnet = subnet
        self.localIntf = localIntf
        self.flush = flush
        self.forwardState = self.cmd( 'sysctl -n net.ipv4.ip_forward' ).strip()

    def setManualConfig( self, intf ):
        """Prevent network-manager/networkd from messing with our interface
           by specifying manual configuration in /etc/network/interfaces"""
        cfile = '/etc/network/interfaces'
        line = '\niface %s inet manual\n' % intf
        try:
            with open( cfile ) as f:
                config = f.read()
        except IOError:
            config = ''
        if ( line ) not in config:
            info( '*** Adding "' + line.strip() + '" to ' + cfile + '\n' )
            with open( cfile, 'a' ) as f:
                f.write( line )
            # Probably need to restart network manager to be safe -
            # hopefully this won't disconnect you
            self.cmd( 'service network-manager restart || netplan apply' )

    # pylint: disable=arguments-differ
    def config( self, **params ):
        """Configure the NAT and iptables"""

        if not self.localIntf:
            self.localIntf = self.defaultIntf()

        self.setManualConfig( self.localIntf )

        # Now we can configure manually without interference
        super( NAT, self).config( **params )

        if self.flush:
            self.cmd( 'sysctl net.ipv4.ip_forward=0' )
            self.cmd( 'iptables -F' )
            self.cmd( 'iptables -t nat -F' )
            # Create default entries for unmatched traffic
            self.cmd( 'iptables -P INPUT ACCEPT' )
            self.cmd( 'iptables -P OUTPUT ACCEPT' )
            self.cmd( 'iptables -P FORWARD DROP' )

        # Install NAT rules
        self.cmd( 'iptables -I FORWARD',
                  '-i', self.localIntf, '-d', self.subnet, '-j DROP' )
        self.cmd( 'iptables -A FORWARD',
                  '-i', self.localIntf, '-s', self.subnet, '-j ACCEPT' )
        self.cmd( 'iptables -A FORWARD',
                  '-o', self.localIntf, '-d', self.subnet, '-j ACCEPT' )
        self.cmd( 'iptables -t nat -A POSTROUTING',
                  '-s', self.subnet, "'!'", '-d', self.subnet,
                  '-j MASQUERADE' )

        # Instruct the kernel to perform forwarding
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        "Stop NAT/forwarding between Mininet and external network"
        # Remote NAT rules
        self.cmd( 'iptables -D FORWARD',
                   '-i', self.localIntf, '-d', self.subnet, '-j DROP' )
        self.cmd( 'iptables -D FORWARD',
                  '-i', self.localIntf, '-s', self.subnet, '-j ACCEPT' )
        self.cmd( 'iptables -D FORWARD',
                  '-o', self.localIntf, '-d', self.subnet, '-j ACCEPT' )
        self.cmd( 'iptables -t nat -D POSTROUTING',
                  '-s', self.subnet, '\'!\'', '-d', self.subnet,
                  '-j MASQUERADE' )
        # Put the forwarding state back to what it was
        self.cmd( 'sysctl net.ipv4.ip_forward=%s' % self.forwardState )
        super( NAT, self ).terminate()


class DockerNode( Node ):
    """
    A virtual node running in a docker container

    Based on https://github.com/p4lang/p4factory
    """
    initialized = False

    def __init__(
        self, name, image=None, publish=None, volume=None, env=None, **kwargs
    ):
        """
        Create a DockerNode based on the provided parameters:
          name: name of the node
          image: docker image to be used
          publish: list of tuples or strings for publishing a container's
             port(s) to the host. Passed to: docker run -p ...
          volume: list of tuples or strings for binding mount a volume from
             host to the container. Passed to: docker run -v ...
          env: list of tuples or strings for set environment variables into the
             container. Passed to: docker run -e ...
       """
        if image is None:
            raise UnboundLocalError("Docker image is not specified")
        self.docker_image = image
        self.publish = publish
        self.volume = volume
        self.env = env
        kwargs["inNamespace"] = True
        Node.__init__(self, name, **kwargs)
        if not DockerNode.initialized:
            DockerNode.initilize()
            DockerNode.initialized = True

    @classmethod
    def initilize(cls):
        """Initilize some routines of the class, for instance adding cleanup"""
        docker = quietRun("which docker").strip()
        if not docker:
            raise ValueError(
                "DockerNode requires docker executable. Is docker installed?"
            )

    @classmethod
    def setup( cls ):
        pass

    def sendCmd( self, *args, **kwargs ):
        assert self.shell and not self.waiting
        printPid = kwargs.get( 'printPid', True )
        # Allow sendCmd( [ list ] )
        if len( args ) == 1 and isinstance( args[ 0 ], list ):
            cmd = args[ 0 ]
        # Allow sendCmd( cmd, arg1, arg2... )
        elif len( args ) > 0:
            cmd = args
        # Convert to string
        if not isinstance( cmd, str ):
            cmd = ' '.join( [ str( c ) for c in cmd ] )
        if not re.search( r'\w', cmd ):
            # Replace empty commands with something harmless
            cmd = 'echo -n'
        self.lastCmd = cmd
        printPid = printPid and not isShellBuiltin( cmd )
        if len( cmd ) > 0 and cmd[ -1 ] == '&':
            # print ^A{pid}\n{sentinel}
            cmd += ' printf "\\001%d\\012" $! '
        else:
            pass
        self.write( cmd + '\n' )
        self.lastPid = None
        self.waiting = True

    def popen( self, *args, **kwargs ):
        mncmd = [ 'docker', 'exec', self.name ]
        return Node.popen( self, *args, mncmd=mncmd, **kwargs )

    def terminate( self ):
        dev_null = open(os.devnull, 'w')
        subprocess.call( [ 'docker rm -f ' + self.name ],
                         stdin=dev_null, stdout=dev_null,
                         stderr=dev_null, shell=True )
        dev_null.close()

    def startShell( self, mnopts=None ):
        args = [
            'docker', 'run', '-ti', '--rm', '--privileged=true',
            '--label=app=mininet',
            '--hostname=' + self.name, '--name=' + self.name,
        ]
        if isinstance(self.publish, list):
            for p in self.publish:
                pub = "%d:%d" % (p[0], p[1]) if isinstance(p, tuple) else p
                args.extend(['-p', pub])
        if isinstance(self.volume, list):
            for v in self.volume:
                vol = "%s:%s" % (v[0], v[1]) if isinstance(v, tuple) else v
                args.extend(['-v', vol])
        if isinstance(self.env, list):
            for e in self.env:
                env = "%s='%s'" % (e[0], e[1]) if isinstance(e, tuple) else e
                args.extend(['-e', env])
        args.extend([self.docker_image, "env", "PS1=" + chr(127), "sh"])

        self.master, self.slave = pty.openpty()
        self.shell = subprocess.Popen(
            args, stdin=self.slave, stdout=self.slave, stderr=self.slave,
            close_fds=True, preexec_fn=os.setpgrp
        )
        self.stdin = os.fdopen( self.master, 'r' )
        self.stdout = self.stdin
        self.pid = self.shell.pid
        self.pollOut = select.poll()
        self.pollOut.register( self.stdout )
        self.outToNode[ self.stdout.fileno() ] = self
        self.inToNode[ self.stdin.fileno() ] = self
        self.execed = False
        self.lastCmd = None
        self.lastPid = None
        self.readbuf = ''
        # Wait for prompt
        while True:
            data = self.read( 1024 )
            if data[ -1 ] == chr( 127 ) or data[0] == chr(127):
                break
            self.pollOut.poll()
        self.waiting = False

        for _ in range(30):
            pid_cmd = ["docker", "inspect", "--format='{{ .State.Pid }}'", self.name]
            pidp = subprocess.run(pid_cmd, capture_output=True, text=True)
            ps_out = pidp.stdout.strip().strip("'\"")
            if ps_out.isdigit():
                break
            time.sleep(1)
        else:
            raise TimeoutError(f"timeout waiting for docker container {self.name} to be created")
        self.pid = int(ps_out)
        self.cmd( 'stty -echo; set +m' )
        if not self.cmd("which ip").strip().endswith("/ip"):
            raise ValueError(
                f"Docker container {self.name} does not have ip command,"
                " cannot proceed! Please use a docker image which includes"
                " ip command."
            )

    @classmethod
    def clean_up(cls):
        containers = quietRun(
            "docker ps -a -f label=app=mininet --format '{{.Names}}'"
        ).strip()
        if not containers:
            return
        containers = " ".join(re.sub("['\"]", "", containers).split())
        info("*** Cleaning up Docker containers\n")
        info(containers + "\n")
        quietRun(f"docker rm -f {containers}")


class DockerSwitch(DockerNode, Switch):
    """A Docker switch is a Docker Node with switch functionality"""
    def start( self, controllers ):
        """Start the switch"""
        pass


class DockerHost(DockerNode, Host):
    """A Docker host is the same as a Docker Node"""
    pass


addCleanupCallback(DockerNode.clean_up)
