Mininet: Rapid Prototyping for Software Defined Networks
========================================================
*The best way to emulate almost any network on your laptop!*

Mininet 2.3.2

[![Build Status][1]](https://github.com/mininet/mininet/actions)


### Heads-Up

Please be advised that this is a fork version from original Mininet at https://github.com/mininet/mininet

This version includes integration with Docker to allow having Docker Nodes inside Mininet. You can also run Mininet as Docker, and then you can have a Docker-in-Docker scenario.

Example 1:

```
$ docker run --privileged -it --rm -v $(pwd)/docker:/var/lib/docker -v /lib/modules:/lib/modules italovalcy/mininet-dind:latest /bin/bash
# mn --topo=linear,3 --host=docker,image=alpine:latest,volume=/tmp/xpto:/tmp/xpto,volume=/tmp/foobar:/tmp/foobar,env=DATA=FoobarXpto,env=DATA2="algo diferente"
*** Error setting resource limits. Mininet's performance may be affected.
*** Creating network
*** Adding controller
*** Adding hosts:
h1 h2 h3
*** Adding switches:
s1 s2 s3
*** Adding links:
(h1, s1) (h2, s2) (h3, s3) (s2, s1) (s3, s2)
*** Configuring hosts
h1 h2 h3
*** Starting controller

*** Starting 3 switches
s1 s2 s3 ...
*** Starting CLI:
mininet> h1 ip link
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: eth0@if23: <BROADCAST,MULTICAST,UP,LOWER_UP,M-DOWN> mtu 1500 qdisc noqueue state UP
    link/ether 7e:0c:6f:81:71:8b brd ff:ff:ff:ff:ff:ff
27: h1-eth0@if26: <BROADCAST,MULTICAST,UP,LOWER_UP,M-DOWN> mtu 1500 qdisc noqueue state UP qlen 1000
    link/ether aa:cd:c8:ee:bb:27 brd ff:ff:ff:ff:ff:ff
mininet> h2 env
HOSTNAME=h2
DATA=FoobarXpto
SHLVL=1
HOME=/root
DATA2=algo diferente
TERM=xterm
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PWD=/
```

Example 2:

```
$ docker run --privileged -it --rm -v $(pwd)/docker:/var/lib/docker -v /lib/modules:/lib/modules italovalcy/mininet-dind:latest /bin/bash
# python3
>>> from mininet.net import Mininet
>>> from mininet.cli import CLI
>>> from mininet.nodelib import DockerHost, DockerSwitch
>>> net = Mininet(controller = None, autoSetMacs=True, autoStaticArp=True)
*** Error setting resource limits. Mininet's performance may be affected.
>>> h1 = net.addHost('h1')
>>> h2 = net.addHost("h2", cls=DockerHost, image="alpine:latest")
>>> h3 = net.addHost('h3', cls=DockerHost, image="busybox:latest")
>>> s1 = net.addSwitch('s1', cls=DockerSwitch, image="amlight/bf-sde:9.13.4")
>>> s2 = net.addSwitch('s2', cls=DockerSwitch, image="amlight/bf-sde:9.13.4")
>>> s3 = net.addSwitch('s3')
>>> net.addLink(s1, h1)
>>> net.addLink(s2, h2)
>>> net.addLink(s3, h3)
>>> net.addLink(s1, s2)
>>> net.addLink(s2, s3)
>>> net.addLink(s3, s1)
>>> net.start()
>>> CLI(net)
```

TODO: adicionar comandos pra setup de s1, s2 e s3


### What is Mininet?

Mininet emulates a complete network of hosts, links, and switches
on a single machine.  To create a sample two-host, one-switch network,
just run:

  `sudo mn`

Mininet is useful for interactive development, testing, and demos,
especially those using OpenFlow and SDN.  OpenFlow-based network
controllers prototyped in Mininet can usually be transferred to
hardware with minimal changes for full line-rate execution.

### How does it work?

Mininet creates virtual networks using process-based virtualization
and network namespaces - features that are available in recent Linux
kernels.  In Mininet, hosts are emulated as `bash` processes running in
a network namespace, so any code that would normally run on a Linux
server (like a web server or client program) should run just fine
within a Mininet "Host".  The Mininet "Host" will have its own private
network interface and can only see its own processes.  Switches in
Mininet are software-based switches like Open vSwitch or the OpenFlow
reference switch.  Links are virtual ethernet pairs, which live in the
Linux kernel and connect our emulated switches to emulated hosts
(processes).

### Features

Mininet includes:

* A command-line launcher (`mn`) to instantiate networks.

* A handy Python API for creating networks of varying sizes and
  topologies.

* Examples (in the `examples/` directory) to help you get started.

* Full API documentation via Python `help()` docstrings, as well as
  the ability to generate PDF/HTML documentation with `make doc`.

* Parametrized topologies (`Topo` subclasses) using the Mininet
  object.  For example, a tree network may be created with the
  command:

  `mn --topo tree,depth=2,fanout=3`

* A command-line interface (`CLI` class) which provides useful
  diagnostic commands (like `iperf` and `ping`), as well as the
  ability to run a command to a node. For example,

  `mininet> h11 ifconfig -a`

  tells host h11 to run the command `ifconfig -a`

* A "cleanup" command to get rid of junk (interfaces, processes, files
  in /tmp, etc.) which might be left around by Mininet or Linux. Try
  this if things stop working!

  `mn -c`

### Python 3 Support

- Mininet 2.3.1b4 supports Python 3 and Python 2

- You can install both the Python 3 and Python 2 versions of
Mininet side by side, but the most recent installation will
determine which Python version is used by default by `mn`.

- You can run `mn` directly with Python 2 or Python 3,
  as long as the appropriate version of Mininet is installed,
  e.g.

      $ sudo python2 `which mn`

- More information regarding Python 3 and Python 2 support
  may be found in the release notes on http://docs.mininet.org.

### Other Enhancements and Information

- Support for Ubuntu 22.04 LTS (and 20.04)

- More reliable testing and CI via github actions

- Preliminary support for cgroups v2 (and v1)

- Minor bug fixes (2.3.1)

- Additional information about this release and previous releases
  may be found in the release notes on http://docs.mininet.org.

### Installation

See `INSTALL` for installation instructions and details.

### Documentation

In addition to the API documentation (`make doc`), much useful
information, including a Mininet walkthrough and an introduction
to the Python API, is available on the
[Mininet Web Site](http://mininet.org).
There is also a wiki which you are encouraged to read and to
contribute to, particularly the Frequently Asked Questions
(FAQ) at http://faq.mininet.org.

### Support

Mininet is community-supported. We encourage you to join the
Mininet mailing list, `mininet-discuss` at:

<https://mailman.stanford.edu/mailman/listinfo/mininet-discuss>

### Join Us

Thanks again to all of the Mininet contributors and users!

Mininet is an open source project and is currently hosted
at <https://github.com/mininet>. You are encouraged to download,
examine, and modify the code, and to submit bug reports, bug fixes,
feature requests, new features, and other issues and pull requests.
Thanks to everyone who has contributed code to the Mininet project
(see CONTRIBUTORS for more info!) It is because of everyone's
hard work that Mininet continues to grow and improve.

### Enjoy Mininet

Have fun! We look forward to seeing what you will do with Mininet
to change the networking world.

Bob Lantz,
on behalf of the Mininet Contributors

[1]: https://github.com/mininet/mininet/workflows/mininet-tests/badge.svg
