import os
from pathlib import Path
from textwrap import dedent

from dotenv import load_dotenv
from invoke import run
from invoke.context import Context
from invoke.tasks import task

load_dotenv()
CONTAINER_NAMES = ["fit-ctf-playground", "fit-ctf-database"]
COMMON_IMAGE = "rockylinux/10"


def is_truthy(value: str) -> bool:
    if value in {"1", "true", "True"}:
        return True
    return False


def curr_dirpath() -> Path:
    return Path(os.path.dirname(os.path.realpath(__file__)))


def get_config(config_name: str) -> Path:
    return curr_dirpath() / "configs" / f"{config_name}.yaml"


def setup_common(c: Context):
    def _get_init(c_name: str) -> str:
        config_path = get_config(f"instance_{c_name}")
        cmd = f"incus init images:{COMMON_IMAGE} {c_name} < {str(config_path)}"
        return cmd

    cmds = []
    cmds.append(f"incus storage create fit-ctf-pool < {str(get_config('pool'))}")
    cmds.append(f"incus network create fitctfbr0 < {str(get_config('network'))}")
    cmds.extend(_get_init(c_name) for c_name in CONTAINER_NAMES)
    c.run(dedent("\n".join(cmds)), shell="/bin/bash")


def setup_playground(c: Context, c_name: str):
    pass


def setup_database(c: Context, c_name: str):
    pass


@task
def setup(c: Context):
    setup_common(c)
        # c.run(f"incus start {c_name}")
        #
        # c.run(f"incus exec {c_name} -- dnf install -y openssh-server", pty=True)
        # c.run(f"incus exec {c_name} -- systemctl enable --now sshd.service", pty=True)


@task
def teardown(c: Context):
    for c_name in CONTAINER_NAMES:
        c.run(f"incus stop --force {c_name}", pty=True, echo=True)
        c.run(f"incus delete {c_name}", pty=True, echo=True)
