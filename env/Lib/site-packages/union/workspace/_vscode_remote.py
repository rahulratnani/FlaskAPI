import random
import string

from flytekit import WorkflowExecutionPhase
from flytekit.models.core.execution import TaskExecutionPhase
from flytekit.models.execution import Execution
from flytekit.models.filters import Equal, ValueIn

from union.remote import UnionRemote

VERSION_STRING_LENGTH = 20


def _generate_random_str(N: int):
    items = string.ascii_letters + string.digits
    return "".join(random.choice(items) for _ in range(N))


def _generate_workspace_name(name: str):
    """Generate workspace name prefixed by name."""
    return f"{name}-{_generate_random_str(VERSION_STRING_LENGTH)}"


def _get_workspace_name(version):
    return version[: -(VERSION_STRING_LENGTH + 1)]


def _get_workspace_executions(remote: UnionRemote, project: str, domain: str):
    executions, _ = remote.client.list_executions_paginated(
        project=project,
        domain=domain,
        limit=1000,
        filters=[
            Equal("task.name", "union.workspace._vscode.workspace"),
            ValueIn("phase", ["RUNNING", "QUEUED"]),
        ],
    )
    return [(e, _get_workspace_name(e.spec.launch_plan.version)) for e in executions]


def _get_vscode_link(remote: UnionRemote, execution: Execution) -> str:
    if execution.closure.phase != WorkflowExecutionPhase.RUNNING:
        return "Unavailable"

    workflow_execution = remote.fetch_execution(
        project=execution.id.project,
        domain=execution.id.domain,
        name=execution.id.name,
    )
    workflow_execution = remote.sync_execution(workflow_execution, sync_nodes=True)

    if not workflow_execution.node_executions:
        return "Unavailable"

    all_keys = [e for e in workflow_execution.node_executions if e != "start-node"]
    if not all_keys:
        return "Unavailable"

    vscode_key = all_keys[0]
    vscode_node = workflow_execution.node_executions[vscode_key]

    if vscode_node.closure.phase != TaskExecutionPhase.RUNNING or not vscode_node.task_executions:
        return "Unavailable"

    task_execution = vscode_node.task_executions[-1]
    if task_execution.closure.phase != TaskExecutionPhase.RUNNING:
        return "Unavailable"

    for log in task_execution.closure.logs:
        if "VSCode" in log.name:
            return remote.generate_console_http_domain() + log.uri
