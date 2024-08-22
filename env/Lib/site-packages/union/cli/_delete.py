from typing import Optional

import rich_click as click
from grpc import RpcError

from union._config import _UNION_DEFAULT_CONFIG_PATH, _get_config_obj
from union.cli._common import _get_channel_with_org
from union.internal.identity.app_payload_pb2 import DeleteAppRequest, GetAppRequest
from union.internal.identity.app_service_pb2_grpc import AppsServiceStub
from union.internal.secret.definition_pb2 import SecretIdentifier
from union.internal.secret.payload_pb2 import DeleteSecretRequest
from union.internal.secret.secret_pb2_grpc import SecretServiceStub
from union.remote import UnionRemote
from union.workspace._vscode_remote import _get_workspace_executions


@click.group()
def delete():
    """Delete a resource."""


@delete.command()
@click.pass_context
@click.argument("name")
@click.option("--project", help="Project name")
@click.option("--domain", help="Domain name")
def secret(
    ctx: click.Context,
    name: str,
    project: Optional[str],
    domain: Optional[str],
):
    """Delete secret with NAME."""
    platform_obj = _get_config_obj(ctx.obj.get("config_file", None)).platform
    channel, org = _get_channel_with_org(platform_obj)

    stub = SecretServiceStub(channel)

    request = DeleteSecretRequest(
        id=SecretIdentifier(name=name, domain=domain, project=project, organization=org),
    )
    try:
        stub.DeleteSecret(request)
        click.echo(f"Deleted secret with name: {name}")
    except RpcError as e:
        raise click.ClickException(f"Unable to delete secret with name: {name}\n{e}") from e


@delete.command()
@click.pass_context
@click.argument("client_id")
def app(
    ctx: click.Context,
    client_id: str,
):
    """Delete app with CLIENT_ID."""
    platform_obj = _get_config_obj(ctx.obj.get("config_file", None)).platform
    channel, org = _get_channel_with_org(platform_obj)

    stub = AppsServiceStub(channel)

    # Get app first to make sure it exist
    get_request = GetAppRequest(organization=org, client_id=client_id)
    try:
        stub.Get(get_request)
    except RpcError as e:
        raise click.ClickException(
            f"Unable to delete app with client_id: {client_id} because it does not exist.\n{e}"
        ) from e

    delete_request = DeleteAppRequest(organization=org, client_id=client_id)
    try:
        stub.Delete(delete_request)
        click.echo(f"Deleted app with client_id: {client_id}")
    except RpcError as e:
        raise click.ClickException(f"Unable to delete app with client_id: {client_id}\n{e}") from e


@delete.command()
def login():
    """Delete login information."""
    if not _UNION_DEFAULT_CONFIG_PATH.exists():
        click.echo(f"Login at {_UNION_DEFAULT_CONFIG_PATH} does not exist. No need to delete.")
        return

    try:
        _UNION_DEFAULT_CONFIG_PATH.unlink()
        click.echo("Deleted login.")
    except Exception as e:
        msg = f"Unable to delete login.\n{e}"
        raise click.ClickException(msg) from e


@delete.command()
@click.pass_context
@click.argument("name")
@click.option("--project", default="system", help="Project name")
@click.option("--domain", default="development", help="Domain name")
def workspace(ctx: click.Context, name: str, project: str, domain: str):
    """Delete workspace with NAME."""
    config_obj = _get_config_obj(ctx.obj.get("config_file", None))
    remote = UnionRemote(config=config_obj, default_domain=domain, default_project=project)

    executions = _get_workspace_executions(remote, project, domain)

    for execution, workspace_name in executions:
        if workspace_name == name:
            remote.terminate(execution, cause="Stopped from CLI")
            click.echo(f"Workspace {name} deleted!")
            break
    else:  # no break
        click.echo(f"Workspace with name: {name} does not exist or no longer running")
