FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND noninteractive

# Install dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends --no-install-suggests \
       openvswitch-switch curl iproute2 iputils-ping net-tools tcpdump jq \
       x11-xserver-utils xterm iperf socat telnet tmux tini procps git-core \
       ca-certificates patch gnupg lsb-release iptables bridge-utils \
       autoconf automake make libtool gcc pkg-config libc6-dev

RUN --mount=type=bind,source=.,target=/mnt/mininet \
  cp -r /mnt/mininet /usr/src/mininet \
  && cd /usr/src/mininet \
  && sed -e 's/sudo //g' \
	 -e 's/DEBIAN_FRONTEND=noninteractive //g' \
	 -e 's/\(apt-get -y -q install\)/\1 --no-install-recommends --no-install-suggests/g' \
         -i ./util/install.sh \
  && rm -f /usr/lib/python3.11/EXTERNALLY-MANAGED \
  && PYTHON=python3 ./util/install.sh -f -n \
  && cd .. && rm -rf /usr/src/* \
  && apt-get purge -y autoconf automake make libtool gcc pkg-config libc6-dev ssh \
  && apt autoremove -y \
  && apt clean \
  && rm -rf /var/lib/apt/lists/*

# Add Docker's official GPG key and repository
RUN install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
 && chmod a+r /etc/apt/keyrings/docker.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" \
    | tee /etc/apt/sources.list.d/docker.list

# Install Docker Engine (Docker-CE)
RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
COPY docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 6633 6653 6640

ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]
