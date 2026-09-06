#!/bin/bash

set -xe

export PATH="$PATH:$HOME/.local/bin"
echo "export PATH=\"$PATH:$HOME/.local/bin\"" >> "$HOME"/.bashrc

dnf update -y
dnf install epel-release -y
dnf install -y git pipx neovim ansible-core

# Prefer IPv4 over IPv6 — Incus bridge has no IPv6 route; ansible-galaxy's
# Python socket tries AAAA first and gets ENETUNREACH. This makes getaddrinfo
# return IPv4 addresses first without disabling IPv6 entirely.
echo "precedence ::ffff:0:0/96  100" >> /etc/gai.conf

ansible-galaxy collection install community.general
ansible-galaxy collection install community.mongodb
ansible-galaxy collection install community.docker
