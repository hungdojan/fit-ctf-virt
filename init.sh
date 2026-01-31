#!/bin/bash
# script for rockylinux/10
set -xe

# install dependencies
dnf install -y git wget epel-release
cd /etc/yum.repos.d && \
    wget https://copr.fedorainfracloud.org/coprs/neelc/incus/repo/rhel+epel-10/neelc-incus-rhel+epel-10.repo
cd -
dnf install incus incus-tools incus-ui
pipx install poetry

# firewall setup
firewall-cmd --add-masquerade --permanent
firewall-cmd --add-interface=incusbr0 --zone=trusted --permanent
firewall-cmd --add-interface=fitctfbr0 --zone=trusted --permanent
firewall-cmd --reload

# configure incus
echo "root:1000000:1000000000" | sudo tee -a /etc/subuid /etc/subgid
systemctl enable --now incus
incus admin init --minimal

# pull configurations
git clone https://github.com/hungdojan/fit-ctf-virt && cd fit-ctf-virt
poetry lock
