"""All imports to unionai in this file should be in the function definition.

This plugin is loaded by flytekit, so any imports to unionai can lead to circular imports.
"""

import json
import re
import shutil
import sys
import tempfile
import warnings
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path
from typing import Optional, Tuple

import click
from flytekit import Labels
from flytekit.core.constants import REQUIREMENTS_FILE_NAME
from flytekit.image_spec.image_spec import _F_IMG_ID, ImageBuildEngine, ImageSpec, ImageSpecBuilder
from flytekit.models.core import execution as core_execution_models
from flytekit.models.filters import ValueIn
from flytekit.remote import FlyteRemote, FlyteWorkflowExecution
from flytekit.remote.remote import MOST_RECENT_FIRST
from flytekit.tools.ignore import DockerIgnore, GitIgnore, IgnoreGroup, StandardIgnore
from flytekit.tools.translator import Options

RECOVER_EXECUTION_PAGE_LIMIT = 1_000
UNIONAI_IMAGE_NAME_KEY = "unionai_image_name"

_PACKAGE_NAME_RE = re.compile(r"^[\w-]+")


def _is_union(package: str) -> bool:
    """Return True if `package` is union or unionai."""
    m = _PACKAGE_NAME_RE.match(package)
    if not m:
        return False
    name = m.group()
    return name in ("union", "unionai")


def get_unionai_for_pypi():
    union_version = version("union")
    if "dev" in union_version:
        return "union"
    else:
        return f"union=={union_version}"


@lru_cache
def _get_remote() -> FlyteRemote:
    from union._config import _should_enable_image_builder
    from union.configuration._plugin import UnionAIPlugin

    remote = UnionAIPlugin.get_remote(
        config=None,
        project="default",
        domain="development",
    )
    if not _should_enable_image_builder(remote.config.platform.endpoint):
        raise ValueError(
            "The UnionAI image builder requires a Serverless endpoint. "
            f"Your current endpoint is {remote.config.platform.endpoint}"
        )
    return remote


@lru_cache
def _get_fully_qualified_image_name(remote, execution):
    return execution.outputs["fully_qualified_image"]


def _build(spec: Path, context: Optional[Path], target_image: str) -> str:
    """Build image using UnionAI."""

    remote = _get_remote()
    start = datetime.now(timezone.utc)

    execution = _get_latest_image_build_execution(remote, target_image)
    if execution is None:
        context_url = "" if context is None else remote.upload_file(context)[1]
        spec_url = remote.upload_file(spec)[1]
        entity = remote.fetch_task(project="system", domain="production", name="build-image")

        execution = remote.execute(
            entity,
            project="system",
            domain="development",
            inputs={"spec": spec_url, "context": context_url, "target_image": target_image},
            options=Options(
                # Replace ':' with '_' since flyte does not allow ':' in the label value
                labels=Labels(values={UNIONAI_IMAGE_NAME_KEY: target_image.replace(":", "_")}),
            ),
        )
        click.secho("👍 Build submitted!", bold=True, fg="yellow")

    console_url = remote.generate_console_url(execution)

    click.secho(
        "⏳ Waiting for build to finish at: " + click.style(console_url, fg="cyan"),
        bold=True,
    )
    execution = remote.wait(execution, poll_interval=timedelta(seconds=1))

    elapsed = str(datetime.now(timezone.utc) - start).split(".")[0]

    if execution.closure.phase == core_execution_models.WorkflowExecutionPhase.SUCCEEDED:
        click.secho(f"✅ Build completed in {elapsed}!", bold=True, fg="green")
    else:
        error_msg = execution.error.message
        raise click.ClickException(
            f"❌ Build failed in {elapsed} at {click.style(console_url, fg='cyan')} with error:\n\n{error_msg}"
        )

    return _get_fully_qualified_image_name(remote, execution)


class UCImageSpecBuilder(ImageSpecBuilder):
    """ImageSpec builder for UnionAI."""

    _SUPPORTED_IMAGE_SPEC_PARAMETERS = {
        "name",
        "builder",
        "python_version",
        "source_root",
        "env",
        "packages",
        "requirements",
        "apt_packages",
        "cuda",
        "cudnn",
        "platform",
        "pip_index",
        "pip_extra_index_url",
        "commands",
    }

    def build_image(self, image_spec: ImageSpec):
        """Build image using UnionAI."""
        image_name = image_spec.image_name()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            spec_path, archive_path = self._validate_configuration(image_spec, tmp_path, image_name)
            return _build(spec_path, archive_path, image_name)

    def should_build(self, image_spec: ImageSpec) -> bool:
        """Check whether the image should be built."""
        image_name = image_spec.image_name()
        remote = _get_remote()
        execution = _get_latest_image_build_execution(remote, image_name)
        if execution is None:
            click.secho(f"Image cr.union.ai/{image_name} not found.", fg="blue")
            click.secho("🐳 Build not found, submitting a new build...", bold=True, fg="blue")
            return True
        elif (
            execution.closure.phase == core_execution_models.WorkflowExecutionPhase.QUEUED
            or execution.closure.phase == core_execution_models.WorkflowExecutionPhase.RUNNING
        ):
            click.secho(f"Image cr.union.ai/{image_name} not found.", fg="blue")
            click.secho("🐳 Build found, but not finished, waiting...", bold=True, fg="blue")
            return True
        else:
            click.secho(f"Image cr.union.ai/{image_name} found. Skip building.", fg="blue")
            # make sure the fully qualified image name is cached in the image builder
            ImageBuildEngine._IMAGE_NAME_TO_REAL_NAME[image_name] = _get_fully_qualified_image_name(remote, execution)
            return False

    def _validate_configuration(
        self, image_spec: ImageSpec, tmp_path: Path, image_name: str
    ) -> Tuple[Path, Optional[Path]]:
        """Validate and write configuration for builder."""
        unsupported_parameters = [
            name
            for name, value in vars(image_spec).items()
            if value is not None and name not in self._SUPPORTED_IMAGE_SPEC_PARAMETERS and not name.startswith("_")
        ]
        if unsupported_parameters:
            msg = f"The following parameters are unsupported and ignored: {unsupported_parameters}"
            warnings.warn(msg, UserWarning)

        # Hardcoded for now since our base image only supports 3.11
        if image_spec.python_version is None:
            major = sys.version_info.major
            minor = sys.version_info.minor
        else:
            version_split = image_spec.python_version.split(".")
            if not (2 <= len(version_split) <= 3):
                raise ValueError("python_version must be in the form major.minor. For example: 3.12")
            major, minor = version_split[:2]
            try:
                major, minor = int(major), int(minor)
            except ValueError:
                raise ValueError("python_version must be in the form major.minor. For example: 3.12")

        if not (major == 3 and 8 <= minor <= 12):
            raise ValueError(f"Only python versions between 3.8 to 3.12 are supported, got {major}.{minor}")

        python_version = f"{major}.{minor}"

        spec = {"python_version": python_version}
        # Transform image spec into a spec we expect
        if image_spec.apt_packages:
            spec["apt_packages"] = image_spec.apt_packages
        if image_spec.commands:
            spec["commands"] = image_spec.commands
        if image_spec.cuda or image_spec.cudnn:
            spec["enable_gpu"] = True

        env = image_spec.env or {}
        env = {**{_F_IMG_ID: image_name}, **env}
        if env:
            spec["env"] = env

        packages = []
        if image_spec.packages:
            packages.extend(image_spec.packages)

        spec["python_packages"] = packages

        pip_extra_index_urls = []
        if image_spec.pip_index:
            pip_extra_index_urls.append(image_spec.pip_index)

        if image_spec.pip_extra_index_url:
            pip_extra_index_urls.extend(image_spec.pip_extra_index_url)

        spec["pip_extra_index_urls"] = pip_extra_index_urls

        context_path = tmp_path / "build.uc-image-builder"
        context_path.mkdir(exist_ok=True)

        _all_packages = []
        _all_packages.extend(packages)

        if image_spec.requirements:
            shutil.copy2(image_spec.requirements, context_path / REQUIREMENTS_FILE_NAME)
            spec["python_requirements_files"] = [REQUIREMENTS_FILE_NAME]

            with (context_path / REQUIREMENTS_FILE_NAME).open() as f:
                _all_packages.extend([line.strip() for line in f.readlines()])

        # if union is not specified, then add it here.
        if not any(_is_union(p) for p in _all_packages):
            packages.append(get_unionai_for_pypi())

        if image_spec.source_root:
            # Easter egg
            # Load in additional packages before installing pip/apt packages
            vendor_path = Path(image_spec.source_root) / ".vendor"
            if vendor_path.is_dir():
                spec["dist_dirpath"] = ".vendor"

            ignore = IgnoreGroup(image_spec.source_root, [GitIgnore, DockerIgnore, StandardIgnore])
            shutil.copytree(
                image_spec.source_root,
                context_path,
                ignore=shutil.ignore_patterns(*ignore.list_ignored()),
                dirs_exist_ok=True,
            )

        if any(context_path.iterdir()):
            archive_path = Path(shutil.make_archive(tmp_path / "context", "xztar", context_path))
        else:
            archive_path = None

        spec_path = tmp_path / "spec.json"
        with spec_path.open("w") as f:
            json.dump(spec, f)

        return (spec_path, archive_path)


def _get_latest_image_build_execution(remote: FlyteRemote, image_name: str) -> Optional[FlyteWorkflowExecution]:
    """
    Get the latest image build execution for the given image name.
    Returns None if no execution is found or the execution is not in QUEUED, RUNNING, or SUCCEEDED phase.
    """
    # Replace ':' with '_' since flyte does not allow ':' in the label value
    target_image = image_name.replace(":", "_")
    executions, _ = remote.client.list_executions_paginated(
        project="system",
        domain="development",
        limit=1,
        filters=[
            ValueIn("execution_tag.key", [UNIONAI_IMAGE_NAME_KEY]),
            ValueIn("execution_tag.value", [target_image]),
            ValueIn("phase", ["QUEUED", "RUNNING", "SUCCEEDED"]),
        ],
        sort_by=MOST_RECENT_FIRST,
    )

    if len(executions) == 0:
        return None

    return remote.sync_execution(FlyteWorkflowExecution.promote_from_model(executions[0]))


def _register_union_image_builder():
    ImageBuildEngine.register("unionai", UCImageSpecBuilder(), priority=10)
    ImageBuildEngine.register("union", UCImageSpecBuilder(), priority=10)
