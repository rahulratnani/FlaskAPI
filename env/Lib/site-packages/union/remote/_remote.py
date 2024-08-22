import logging
import typing

from flyteidl.core import artifact_id_pb2 as art_id
from flytekit.clients.friendly import SynchronousFlyteClient
from flytekit.configuration import Config
from flytekit.core.type_engine import LiteralsResolver, TypeEngine
from flytekit.exceptions import user as user_exceptions
from flytekit.models.core.identifier import ResourceType
from flytekit.remote import FlyteRemote
from flytekit.remote.entities import FlyteLaunchPlan, FlyteTask, FlyteWorkflow
from flytekit.remote.executions import FlyteNodeExecution, FlyteTaskExecution, FlyteWorkflowExecution
from flytekit.tools.translator import (
    Options,
)

from union._config import _get_config_obj, _get_organization
from union._interceptor import update_client_with_interceptor
from union.artifacts import Artifact
from union.internal.artifacts import artifacts_pb2, artifacts_pb2_grpc

SERVERLESS_VANITY_URLS = {
    "https://serverless-1.us-east-2.s.union.ai": "https://serverless.union.ai",
    "https://serverless-preview.canary.unionai.cloud": "https://serverless.canary.union.ai",
    "https://serverless-gcp.cloud-staging.union.ai": "https://serverless.staging.union.ai",
}


class UnionRemote(FlyteRemote):
    def __init__(
        self,
        config: typing.Optional[Config] = None,
        default_project: typing.Optional[str] = "default",
        default_domain: typing.Optional[str] = "development",
        data_upload_location: str = "flyte://my-s3-bucket/",
        **kwargs,
    ):
        if config is None:
            config = _get_config_obj(config, default_to_union_semantics=True)

        super().__init__(config, default_project, default_domain, data_upload_location, **kwargs)
        self._artifacts_client = None

    @property
    def client(self) -> SynchronousFlyteClient:
        """Return a SynchronousFlyteClient for additional operations."""
        if not self._client_initialized:
            client = SynchronousFlyteClient(self.config.platform, **self._kwargs)
            org = _get_organization(self.config.platform, channel=client._channel)
            self._client = update_client_with_interceptor(client, org)
            self._client_initialized = True

        return self._client

    def generate_console_http_domain(self) -> str:
        default_console_http_domain = super().generate_console_http_domain()
        return SERVERLESS_VANITY_URLS.get(default_console_http_domain, default_console_http_domain)

    def generate_console_url(
        self,
        entity: typing.Union[
            FlyteWorkflowExecution, FlyteNodeExecution, FlyteTaskExecution, FlyteWorkflow, FlyteTask, FlyteLaunchPlan
        ],
    ):
        """
        Generate a UnionAI console URL for the given Flyte remote endpoint.

        This will automatically determine if this is an execution or an entity
        and change the type automatically.
        """
        org = _get_organization(self.config.platform)
        if org == "":
            return super().generate_console_url(entity)

        if isinstance(entity, (FlyteWorkflowExecution, FlyteNodeExecution, FlyteTaskExecution)):
            return (
                f"{self.generate_console_http_domain()}/org/{org}/projects/{entity.id.project}/domains/"
                f"{entity.id.domain}/executions/{entity.id.name}"
            )  # noqa

        if not isinstance(entity, (FlyteWorkflow, FlyteTask, FlyteLaunchPlan)):
            raise ValueError(f"Only remote entities can be looked at in the console, got type {type(entity)}")
        rt = "workflow"
        if entity.id.resource_type == ResourceType.TASK:
            rt = "task"
        elif entity.id.resource_type == ResourceType.LAUNCH_PLAN:
            rt = "launch_plan"
        return (
            f"{self.generate_console_http_domain()}/org/{org}/projects/{entity.id.project}/"
            f"domains/{entity.id.domain}/{rt}/{entity.name}/version/{entity.id.version}"
        )  # noqa

    @property
    def artifacts_client(self) -> artifacts_pb2_grpc.ArtifactRegistryStub:
        if self._artifacts_client:
            return self._artifacts_client

        self._artifacts_client = artifacts_pb2_grpc.ArtifactRegistryStub(self.client._channel)
        return self._artifacts_client

    def get_artifact(
        self,
        uri: typing.Optional[str] = None,
        artifact_key: typing.Optional[art_id.ArtifactKey] = None,
        artifact_id: typing.Optional[art_id.ArtifactID] = None,
        query: typing.Optional[art_id.ArtifactQuery] = None,
        get_details: bool = False,
    ) -> typing.Optional[Artifact]:
        """
        Get the specified artifact.

        :param uri: An artifact URI.
        :param artifact_key: An artifact key.
        :param artifact_id: The artifact ID.
        :param query: An artifact query.
        :param get_details: A bool to indicate whether or not to return artifact details.
        :return: The artifact as persisted in the service.
        """
        if query:
            q = query
        elif uri:
            q = art_id.ArtifactQuery(uri=uri)
        elif artifact_key:
            q = art_id.ArtifactQuery(artifact_id=art_id.ArtifactID(artifact_key=artifact_key))
        elif artifact_id:
            q = art_id.ArtifactQuery(artifact_id=artifact_id)
        else:
            raise ValueError("One of uri, key, id")
        req = artifacts_pb2.GetArtifactRequest(query=q, details=get_details)
        resp = self.artifacts_client.GetArtifact(req)
        a = Artifact.from_flyte_idl(resp.artifact)
        if a.literal and a.name:
            # assigned here because the resolver has an implicit dependency on the remote's context
            # can move into artifact if we are okay just using the current context.
            a.resolver = LiteralsResolver(literals={a.name: a.literal}, variable_map=None, ctx=self.context)
        return a

    def _execute(
        self,
        entity: typing.Union[FlyteTask, FlyteWorkflow, FlyteLaunchPlan],
        inputs: typing.Dict[str, typing.Any],
        project: str = None,
        domain: str = None,
        execution_name: typing.Optional[str] = None,
        execution_name_prefix: typing.Optional[str] = None,
        options: typing.Optional[Options] = None,
        wait: bool = False,
        type_hints: typing.Optional[typing.Dict[str, typing.Type]] = None,
        overwrite_cache: typing.Optional[bool] = None,
        envs: typing.Optional[typing.Dict[str, str]] = None,
        tags: typing.Optional[typing.List[str]] = None,
        cluster_pool: typing.Optional[str] = None,
        **kwargs,
    ) -> FlyteWorkflowExecution:
        resolved_inputs = {}
        for k, v in inputs.items():
            # TODO: Remove when https://github.com/flyteorg/flytekit/pull/2136 gets merged
            if Artifact is None:
                resolved_inputs[k] = v
            elif isinstance(v, artifacts_pb2.Artifact):
                lit = v.spec.value
                resolved_inputs[k] = lit
            elif isinstance(v, Artifact):
                if v.literal is not None:
                    lit = v.literal
                elif v.to_id_idl() is not None:
                    fetched_artifact = self.get_artifact(artifact_id=v.concrete_artifact_id)
                    if not fetched_artifact:
                        raise user_exceptions.FlyteValueException(
                            v.concrete_artifact_id, "Could not find artifact with ID given"
                        )
                    lit = fetched_artifact.literal
                else:
                    raise user_exceptions.FlyteValueException(
                        v, "When binding input to Artifact, either the Literal or the ID must be set"
                    )
                resolved_inputs[k] = lit
            else:
                resolved_inputs[k] = v

        return super()._execute(
            entity,
            resolved_inputs,
            project=project,
            domain=domain,
            execution_name=execution_name,
            execution_name_prefix=execution_name_prefix,
            options=options,
            wait=wait,
            type_hints=type_hints,
            overwrite_cache=overwrite_cache,
            envs=envs,
            tags=tags,
            cluster_pool=cluster_pool,
            **kwargs,
        )

    def create_artifact(self, artifact: Artifact):
        """
        Create an artifact in FlyteAdmin.

        :param artifact: The artifact to create.
        :return: The artifact as persisted in the service.
        """
        # Two things can happen here -
        #  - the call to to_literal may upload something, in the case of an offloaded data type.
        #    - if this happens, the upload request should already return the created Artifact object.
        if artifact.literal is None:
            with self.remote_context() as ctx:
                lt = artifact.literal_type or TypeEngine.to_literal_type(artifact.python_type)
                lit = TypeEngine.to_literal(ctx, artifact.python_val, artifact.python_type, lt)
                artifact.literal_type = lt.to_flyte_idl()
                artifact.literal = lit.to_flyte_idl()
        else:
            raise ValueError("Cannot create an artifact with a literal already set.")

        if artifact.project is None:
            artifact.project = self.default_project
        if artifact.domain is None:
            artifact.domain = self.default_domain
        create_request = Artifact.to_create_request(artifact)
        logging.debug(f"CreateArtifact request {create_request}")
        resp = self.artifacts_client.CreateArtifact(create_request)
        logging.debug(f"CreateArtifact response {resp}")
