#!/bin/bash

set -xe

export PATH="$PATH:$HOME/.local/bin"
echo "export PATH=\"$PATH:$HOME/.local/bin\"" >> "$HOME"/.bashrc

dnf update -y
dnf install epel-release -y
dnf install -y git pipx neovim ansible-core

ansible-galaxy collection install community.general
ansible-galaxy collection install community.mongodb
ansible-galaxy collection install community.docker
