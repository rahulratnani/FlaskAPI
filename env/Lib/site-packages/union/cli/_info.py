from importlib.metadata import version
from textwrap import dedent

import rich
import rich_click as click
from rich.panel import Panel

from union._config import _get_config_obj


@click.command("info")
@click.pass_context
def info(ctx: click.Context):
    config_obj = _get_config_obj(ctx.obj.get("config_file", None))
    endpoint = config_obj.platform.endpoint

    union_version = version("union")
    flytekit_version = version("flytekit")
    context = dedent(
        f"""
    union is the CLI to interact with Union. Use the CLI to register, create and track task and workflow executions locally and remotely.

    Union Version    : {union_version}
    Flytekit Version : {flytekit_version}
    Union Endpoint   : {endpoint}
    """  # noqa
    )

    rich.print(Panel(context, title="Union CLI Info"))
