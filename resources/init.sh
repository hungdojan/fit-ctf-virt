#!/bin/bash

set -xe

export PATH="$PATH:$HOME/.local/bin"
echo "export PATH=\"$PATH:$HOME/.local/bin\"" >> "$HOME"/.bashrc
#
# dnf update
# dnf install epel-release -y
# dnf install -y git pipx neovim
#
# pipx install --include-deps ansible
cd /tmp/setup/ansible
ansible-playbook playbooks/main.yaml --extra-vars "@/tmp/setup/vals.yaml"
