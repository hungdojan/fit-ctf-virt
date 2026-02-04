import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Literal

import yaml
from invoke import run
from invoke.context import Context
from invoke.tasks import task
from jinja2 import Environment, FileSystemLoader


def root_dirpath() -> Path:
    return Path(os.path.dirname(os.path.realpath(__file__)))


def get_config() -> dict:
    data = {}
    config_file = root_dirpath() / "env-config.yaml"
    if not config_file.exists():
        raise FileNotFoundError("File `env-config.yaml` not found.")
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
    return data


def generate_extra_vars(envs: dict, instance_name: str):
    resource_dir = root_dirpath() / "resources"
    env = Environment(loader=FileSystemLoader(resource_dir))
    template = env.get_template("ansible_extra_vals.yaml.j2")
    output_dir = resource_dir / instance_name
    out_vals_fp = output_dir / "vals.yaml"
    with open(out_vals_fp, "w") as f:
        f.write(template.render(envs=envs))


def copy_init_script(instance_name: str):
    resource_dir = root_dirpath() / "resources"
    output_dir = resource_dir / instance_name
    src_script = resource_dir / "init.sh"
    dst_script = output_dir / "init.sh"
    shutil.copy(src=src_script, dst=dst_script)


def setup_storage(c: Context, config: dict):
    name = config["name"]
    result = run(f"incus storage list --format json", hide=True, warn=True)
    if result:
        data = [d for d in json.loads(result.stdout) if d["name"] == name]
        if data:
            print(f"Storage {name} already exist")
            return

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as storage_config:
        storage_type = config["driver"]
        yaml.safe_dump(
            config,
            storage_config,
            default_flow_style=False,
            sort_keys=False,
        )
        config_path = Path(storage_config.name)
        cmd = f"incus storage create {name} {storage_type} < {str(config_path)}"
        c.run(cmd, echo=True, pty=True)


def wait_for_ip(c: Context, instance_name: str, host_target: str, timeout: int = 120):
    start = time.time()
    while time.time() - start < timeout:
        result = c.run(f"incus list {instance_name} --format json", hide=True)
        try:
            data = json.loads(result.stdout)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing JSON: {e}")
            raise
        if data[0].get("state", {}).get("network", {}):
            network = data[0]["state"]["network"]
            for interface in network.values():
                for address in interface["addresses"]:
                    if address["family"] != "inet":
                        continue
                    if address["address"] == host_target:
                        return
        print("Waiting for machine to boot up...")
        time.sleep(2)
    raise TimeoutError(f"{instance_name} did not start within {timeout}s")


def setup_network(c: Context, config: dict):
    name = config["name"]
    result = run(f"incus network list --format json", hide=True, warn=True)
    if result:
        data = [d for d in json.loads(result.stdout) if d["name"] == name]
        if data:
            print(f"Network {name} already exist")
            return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as network_config:
        yaml.safe_dump(
            config,
            network_config,
            default_flow_style=False,
            sort_keys=False,
        )
        config_path = Path(network_config.name)
        cmd = f"incus network create {name} < {str(config_path)}"
        c.run(cmd, echo=True, pty=True)


def setup_profile(c: Context, config: dict):
    name = config["name"]
    result = run(f"incus profile list --format json", hide=True, warn=True)
    if result:
        data = [d for d in json.loads(result.stdout) if d["name"] == name]
        if data:
            print(f"Profile {name} already exist")
            return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as profile_config:
        yaml.safe_dump(
            config,
            profile_config,
            default_flow_style=False,
            sort_keys=False,
        )
        config_path = Path(profile_config.name)
        cmd = f"incus profile create {name} < {str(config_path)}"
        c.run(cmd, echo=True, pty=True)


def setup_playground(c: Context, config: dict):
    name = config["name"]
    result = run(f"incus list --format json", hide=True, warn=True)
    if result:
        data = [d for d in json.loads(result.stdout) if d["name"] == name]
        if data:
            print(f"Instance {name} already exist")
            return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as playground_config:
        image = config["config"].pop("image", "")
        use_vm = config["config"]["type"] == "virtual-machine"
        yaml.safe_dump(
            config["config"],
            playground_config,
            default_flow_style=False,
            sort_keys=False,
        )
        config_path = Path(playground_config.name)
        cmd = f"incus init images:{image} {name} {'--vm' if use_vm else ''} < {str(config_path)}"
        c.run(cmd, echo=True, pty=True)


def setup_database(c: Context, config: dict):
    name = config["name"]
    result = run(f"incus list --format json", hide=True, warn=True)
    if result:
        data = [d for d in json.loads(result.stdout) if d["name"] == name]
        if data:
            print(f"Instance {name} already exist")
            return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as database_config:
        name = config["name"]
        image = config["config"].pop("image", "")
        yaml.safe_dump(
            config["config"],
            database_config,
            default_flow_style=False,
            sort_keys=False,
        )
        config_path = Path(database_config.name)
        cmd = f"incus init images:{image} {name} < {str(config_path)}"
        c.run(cmd, echo=True, pty=True)


def instance_is_running(c: Context, instance_name: str):
    result = run(
        f"incus list {instance_name} status=RUNNING -c n,s --format csv",
        hide=True,
        warn=True,
    )
    return result and result.stdout


def delete_object(
    c: Context,
    name: str,
    obj_name: Literal["storage", "network", "profile", "instance"],
):
    result = run(
        f"incus {obj_name if obj_name != 'instance' else ''} list --format json",
        hide=True,
        warn=True,
    )
    if not result:
        print(f"{obj_name.capitalize()} {name} not found")
        return
    data = [d for d in json.loads(result.stdout) if d["name"] == name]
    if not data:
        print(f"{obj_name.capitalize()} {name} not found")
        return
    if obj_name == "instance" and instance_is_running(c, name):
        c.run(f"incus stop {name}")
    c.run(
        f"incus {obj_name if obj_name != 'instance' else ''} delete {name}",
        echo=True,
        pty=True,
    )


@task
def setup(c: Context):
    config = get_config()
    setup_storage(c, config["common"]["storage"])
    setup_network(c, config["common"]["network"])
    setup_profile(c, config["common"]["profile"])
    setup_playground(c, config["playground"])
    setup_database(c, config["database"])


def init_instance(
    c: Context, config: dict, resource_name: str, extra_vars: bool = True
):
    name = config[resource_name]["name"]
    resource_dir = root_dirpath() / "resources" / resource_name
    if not instance_is_running(c, name):
        c.run(f"incus start {name}", echo=True)

    wait_for_ip(
        c, name, config[resource_name]["config"]["devices"]["eth0"]["ipv4.address"]
    )
    if extra_vars:
        generate_extra_vars(config[resource_name]["envs"], resource_name)
    copy_init_script(resource_name)
    c.run(
        f"incus file push -r {str(resource_dir)}/* {name}/tmp/setup/",
        echo=True,
        pty=True,
    )
    c.run(
        f"""
        # Set ownership to root (or another user)
        incus exec {name} -- chown -R root:root /tmp/setup

        # Make scripts executable
        incus exec {name} -- chmod -R 755 /tmp/setup
        """
    )
    c.run(f"incus exec {name} -- bash /tmp/setup/init.sh", echo=True)
    ansible_cmd = (
        f"cd /tmp/setup/ansible && ansible-playbook -i inventory.ini playbook.yaml"
    )
    if extra_vars:
        ansible_cmd += " --extra-vars '@/tmp/setup/vals.yaml'"
    c.run(f'incus exec {name} -- bash -c "{ansible_cmd}"', echo=True)
    c.run(f"incus exec {name} -- rm -rf /tmp/setup", echo=True)


@task
def init_playground(c: Context):
    config = get_config()
    init_instance(c, config, "playground")


@task
def init_database(c: Context):
    config = get_config()
    init_instance(c, config, "database")


@task
def teardown(c: Context):
    config = get_config()
    delete_object(c, config["database"]["name"], "instance")
    delete_object(c, config["playground"]["name"], "instance")
    delete_object(c, config["common"]["profile"]["name"], "profile")
    delete_object(c, config["common"]["network"]["name"], "network")
    delete_object(c, config["common"]["storage"]["name"], "storage")
