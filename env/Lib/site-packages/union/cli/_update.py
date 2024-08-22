from typing import Optional

import rich_click as click
from grpc import RpcError

from union._config import _get_config_obj
from union.cli._common import _get_channel_with_org
from union.cli._option import MutuallyExclusiveOption
from union.internal.secret.definition_pb2 import SecretIdentifier, SecretSpec
from union.internal.secret.payload_pb2 import UpdateSecretRequest
from union.internal.secret.secret_pb2_grpc import SecretServiceStub


@click.group()
def update():
    """Update a resource."""


@update.command()
@click.pass_context
@click.argument("name")
@click.option(
    "--value",
    help="Secret value",
    prompt="Enter secret value",
    hide_input=True,
    cls=MutuallyExclusiveOption,
    mutually_exclusive=["value_file"],
)
@click.option(
    "-f",
    "--value-file",
    help="Path to file containing the secret",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, allow_dash=True),
    cls=MutuallyExclusiveOption,
    mutually_exclusive=["value"],
)
@click.option("--project", help="Project name")
@click.option("--domain", help="Domain name")
def secret(
    ctx: click.Context,
    name: str,
    value: str,
    value_file: str,
    project: Optional[str],
    domain: Optional[str],
):
    """Update secret with NAME."""
    platform_obj = _get_config_obj(ctx.obj.get("config_file", None)).platform
    channel, org = _get_channel_with_org(platform_obj)

    if value_file:
        with open(value_file, "rb") as f:
            secret_spec = SecretSpec(binary_value=f.read())
    else:
        secret_spec = SecretSpec(string_value=value)

    stub = SecretServiceStub(channel)
    request = UpdateSecretRequest(
        id=SecretIdentifier(name=name, domain=domain, project=project, organization=org),
        secret_spec=secret_spec,
    )

    try:
        stub.UpdateSecret(request)
        click.echo(f"Updated secret with name: {name}")
    except RpcError as e:
        raise click.ClickException(f"Unable to update secret with name: {name}\n{e}") from e
