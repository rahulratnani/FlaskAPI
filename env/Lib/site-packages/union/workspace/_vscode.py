import inspect
import os
import platform
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from multiprocessing import Process
from pathlib import Path
from shutil import which
from string import Template
from subprocess import run
from textwrap import dedent
from time import sleep, time
from typing import List, Optional, Union

import flytekit
import fsspec
from flytekit import ImageSpec, PythonFunctionTask, Resources, current_context
from flytekit.configuration import AuthType, SerializationSettings
from flytekit.core.base_task import Task
from flytekit.core.context_manager import FlyteContextManager
from flytekit.core.utils import ClassDecorator
from flytekit.extend import TaskResolverMixin
from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.mixins.yaml import DataClassYAMLMixin

VSCODE_TYPE_VALUE = "vscode"
# Config keys to store in task template
TASK_FUNCTION_SOURCE_PATH = "TASK_FUNCTION_SOURCE_PATH"

CODE_SERVER_CLI_NAME = "code-server"
DEFAULT_PORT = 8080
DOWNLOAD_DIR = Path.home() / ".code-server"
WORKSPACE_DIR = Path("/workspace")
HEARTBEAT_PATH = Path.home() / ".local" / "share" / "code-server" / "heartbeat"
CODE_SERVER_VERSION = "4.23.1"
CODE_SERVER_DOWNLOAD_URL = (
    "https://github.com/coder/code-server/releases/download/v{version}/code-server-{version}-linux-{arch}.tar.gz"
)
CODE_SERVER_CLI_NAME_TEMPLATE = "code-server-{version}-linux-{arch}"
HEARTBEAT_CHECK_SECONDS = 60
# 20 minutes is the default up time
DEFAULT_UP_SECONDS = 20 * 60

ROOT_PATH = Path.home()
BASHRC_PATH = Path.home() / ".bashrc"
UNION_GITHUB_TOKEN_ENV = "UNION_WORKSPACE_GITHUB_TOKEN"
UNION_SERVERLESS_API_KEY_ENV = "UNION_WORKSPACE_SERVERLESS_API_KEY"
GIT_CONFIG_PATH = Path.home() / ".gitconfig"


GIT_CONFIG_TEMPLATE = Template(
    """\
$USER_INFO

[credential "https://github.com"]
    helper =
    helper = !/usr/bin/gh auth git-credential
[credential "https://gist.github.com"]
    helper =
    helper = !/usr/bin/gh auth git-credential

[url "https://$GITHUB_TOKEN@github.com/"]
    insteadOf = https://github.com/
"""
)

_DEFAULT_CONFIG_YAML_FOR_BASE_IMAGE = """\
name: my-workspace
# Make sure that the project and domain exists
project: flytesnacks
domain: development
container_image: ghcr.io/unionai/workspace:0.0.9

resources:
    cpu: "2"
    mem: "4Gi"
    gpu: null

workspace_root: ~/workspace
on_startup: null
metadata: null
"""

_DEFAULT_CONFIG_YAML_FOR_IMAGE_SPEC = """\
name: my-workspace
project: default
domain: development
container_image:
    builder: "union"

resources:
    cpu: "2"
    mem: "4Gi"
    gpu: null

on_startup: null
metadata: null
"""


class ImageSpecConfig(DataClassYAMLMixin, DataClassJSONMixin, ImageSpec):
    def __hash__(self):
        return hash(self.to_dict().__str__())


class ResourceConfig(DataClassYAMLMixin, Resources):
    pass


@dataclass
class WorkspaceConfig(DataClassYAMLMixin, DataClassJSONMixin):
    name: str
    project: str
    domain: str
    container_image: Optional[Union[ImageSpecConfig, str]]
    resources: Optional[ResourceConfig] = None
    workspace_root: str = "/workspace"
    on_startup: Optional[str] = None

    def __post_init__(self):
        # Quick hack to always build image
        if not isinstance(self.container_image, str) and os.getenv("UNION_DEV"):
            from union._testing import imagespec_with_local_union
            from union.ucimage._image_builder import _register_union_image_builder

            _register_union_image_builder()
            image_spec = imagespec_with_local_union()
            self.container_image = ImageSpecConfig(
                name="workspace",
                builder="union",
                packages=image_spec.packages + ["keyrings.alt"],
                source_root=image_spec.source_root,
                apt_packages=["git", "sudo", "wget", "vim"],
                commands=[
                    "wget https://github.com/cli/cli/releases/download/v2.49.0/gh_2.49.0_linux_amd64.deb "
                    "-O /tmp/gh.deb",
                    "apt install /tmp/gh.deb",
                    "wget https://github.com/coder/code-server/releases/download/v4.23.1/code-server_4.23.1_amd64.deb "
                    "-O /tmp/code-server.deb",
                    "apt install /tmp/code-server.deb",
                ],
            )


def configure_python_path():
    python_bin = os.path.dirname(sys.executable)
    with BASHRC_PATH.open("a") as f:
        f.write(os.linesep)
        f.write(f"export PATH={python_bin}:$PATH")
        f.write(os.linesep)
        f.write(r'export PS1="\[\e[0;34m\]\w\[\e[m\]\$ "')


def configure_union_remote(host: str):
    from union._config import _write_config_to_path

    _write_config_to_path(host, AuthType.DEVICEFLOW.value)


def configure_git(repo: str, workspace_dir: Path, git_name: str, git_email: str) -> str:
    """Configures workspace built with ImageSpec on Union's hosted image builder."""

    ctx = current_context()
    secrets = ctx.secrets

    with BASHRC_PATH.open("a") as f:
        github_token = secrets.get(key=UNION_GITHUB_TOKEN_ENV)
        f.write(f"export GITHUB_TOKEN={github_token}")

    user_info = dedent(
        f"""\
    [user]
        name = {git_name}
        email = {git_email}
    """
    )
    git_config = GIT_CONFIG_TEMPLATE.substitute(
        USER_INFO=user_info,
        GITHUB_TOKEN=github_token,
    )

    GIT_CONFIG_PATH.write_text(git_config)

    root_dir = workspace_dir

    if repo != "":
        workspace_dir.mkdir(exist_ok=True)
        subprocess.run(["/usr/bin/git", "clone", repo], cwd=workspace_dir, text=True)
        for item in workspace_dir.iterdir():
            if item.is_dir():
                root_dir = item
                break
    return root_dir


class vscode(ClassDecorator):
    """Union specific VSCode extension."""

    def __init__(self, task_function: Optional[callable] = None):
        super().__init__(task_function=task_function)

    def execute(self, *args, **kwargs):
        ctx = FlyteContextManager.current_context()
        ctx.user_space_params.builder().add_attr(
            TASK_FUNCTION_SOURCE_PATH, inspect.getsourcefile(self.task_function)
        ).build()

        if ctx.execution_state.is_local_execution():
            return

        self.task_function(*args, **kwargs)

    def get_extra_config(self):
        return {self.LINK_TYPE_KEY: VSCODE_TYPE_VALUE, self.PORT_KEY: f"{DEFAULT_PORT}"}


@vscode
def workspace(config_content: str, host: str):
    ROOT_PATH.mkdir(exist_ok=True)
    configure_python_path()
    configure_union_remote(host)

    workspace_config = WorkspaceConfig.from_yaml(config_content)
    workspace_dir = Path(workspace_config.workspace_root).expanduser()

    workspace_dir.mkdir(exist_ok=True)
    config_path = workspace_dir / "config.yaml"
    config_path.write_text(config_content)

    on_startup = workspace_config.on_startup
    if on_startup is not None:
        commands = on_startup.split()
        subprocess.run(commands, cwd=workspace_dir, text=True)

    start_vscode_service(workspace_dir)


class WorkspaceResolver(TaskResolverMixin):
    @property
    def location(self) -> str:
        return "union.workspace._vscode.resolver"

    @property
    def name(self) -> str:
        return "union.workspace.vscode"

    def get_task_for_workspace(
        self,
        config: WorkspaceConfig,
    ) -> PythonFunctionTask:
        return PythonFunctionTask(
            task_config=None,
            task_function=workspace,
            task_type="workspace",
            task_resolver=self,
            requests=config.resources,
            container_image=config.container_image,
        )

    def load_task(self, loader_args: List[str]) -> PythonFunctionTask:
        return PythonFunctionTask(
            task_config=None,
            task_function=workspace,
            task_type="workspace",
            task_resolver=self,
        )

    def loader_args(self, settings: SerializationSettings, task: PythonFunctionTask) -> List[str]:
        return ["workspace"]

    def get_all_tasks(self) -> List[Task]:
        raise NotImplementedError


resolver = WorkspaceResolver()


def download_http(url: str, local_dest_path: Path) -> Path:
    """Download URL to `download_dir`. Returns Path of downloaded file."""
    logger = flytekit.current_context().logging

    fs = fsspec.filesystem("http")
    logger.info(f"Downloading {url} to {local_dest_path}")
    fs.get(url, local_dest_path)
    logger.info("File downloaded successfully!")

    return local_dest_path


def download_and_configure_vscode(version: str) -> str:
    """Download and configure vscode."""
    logger = flytekit.current_context().logging
    code_server_cli = which(CODE_SERVER_CLI_NAME)
    if code_server_cli is not None:
        logger.info(f"Code server binary already exists at {code_server_cli}")
        logger.info("Skipping downloading coe server")
        return code_server_cli

    # Download code-server
    logger.info(f"Code server is not in $PATH, downloading code server to {DOWNLOAD_DIR}...")
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    machine_info = platform.machine()
    logger.info(f"machine type: {machine_info}")

    if machine_info == "aarch64":
        arch = "arm64"
    elif machine_info == "x86_64":
        arch = "amd64"
    else:
        msg = (
            "Automatic download is only supported on AMD64 and ARM64 architectures. "
            "If you are using a different architecture, please visit the code-server official "
            "website to manually download the appropriate version for your image."
        )
        raise ValueError(msg)

    code_server_tar_path_url = CODE_SERVER_DOWNLOAD_URL.format(version=version, arch=arch)
    code_server_local_path = DOWNLOAD_DIR / "code-server.tar.gz"
    download_http(code_server_tar_path_url, code_server_local_path)
    with tarfile.open(code_server_local_path, "r:gz") as tar:
        tar.extractall(path=DOWNLOAD_DIR)

    code_server_cli = (
        DOWNLOAD_DIR / CODE_SERVER_CLI_NAME_TEMPLATE.format(version=version, arch=arch) / "bin" / CODE_SERVER_CLI_NAME
    )
    return os.fspath(code_server_cli)


def monitor_vscode(child_process):
    logger = flytekit.current_context().logging
    start_time = time()

    while True:
        if not HEARTBEAT_PATH.exists():
            delta = time() - start_time
        else:
            delta = time() - HEARTBEAT_PATH.stat().st_mtime

        logger.info(f"The latest activity on code server was {delta} ago.")
        if delta > DEFAULT_UP_SECONDS:
            logger.info(f"code server is idle for more than {DEFAULT_UP_SECONDS} seconds. Terminating...")
            child_process.terminate()
            child_process.join()
            sys.exit(0)

        sleep(HEARTBEAT_CHECK_SECONDS)


def start_vscode_service(workspace_root: Path):
    code_server_cli = download_and_configure_vscode(CODE_SERVER_VERSION)

    host = f"0.0.0.0:{DEFAULT_PORT}"

    command = [
        code_server_cli,
        "--bind-addr",
        host,
        "--disable-workspace-trust",
        "--auth",
        "none",
    ]

    workspace_root = workspace_root.absolute()

    command.append(os.fspath(workspace_root))

    child_process = Process(target=run, args=[command], kwargs={"text": True})
    child_process.start()
    monitor_vscode(child_process)
