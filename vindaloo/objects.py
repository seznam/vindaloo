import copy
from typing import Union, Dict as DictType, List as ListType

__all__ = (
    'Dict',
    'List',
    'PortsList',
    'Container',
    'Deployment',
    'CronJob',
    'Job',
    'Service',
)


class JsonSerializable:
    NAME = "undefined"

    def serialize(self, app=None):
        raise NotImplementedError()

    def clone(self):
        return copy.deepcopy(self)

    def __str__(self):
        return str(f'{self.NAME}({self.serialize()})')

    def __setattr__(self, key, value):
        if key not in self.__slots__:
            raise NotImplementedError(f"Property {key} is not supported")
        super().__setattr__(key, value)


class Dict(JsonSerializable):
    __slots__ = ('children',)

    NAME = 'Dict'

    def __init__(self, *args, **kwargs):
        if kwargs:
            self.children = kwargs
        elif args:
            self.children = args[0] or {}
        else:
            self.children = {}

    def serialize(self, app=None):
        return {
            key: val.serialize(app) if isinstance(val, Dict) else val
            for key, val in self.children.items()
        }

    def __getattr__(self, key):
        if key not in self.children:
            self.children[key] = Dict()
        return self.children[key]

    def __setattr__(self, key, val):
        if key in ('children', 'NAME'):
            super().__setattr__(key, val)
        else:
            if isinstance(val, dict):
                val = Dict(val)

            self.children[key] = val

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __setitem__(self, key, value):
        self.children[key] = value

    def __deepcopy__(self, memo):
        return self.__class__(copy.deepcopy(self.children, memo))


class List(Dict):
    NAME = 'List'
    VALUE_KEY = 'value'

    def serialize(self, app=None):
        items = []

        for key, val in self.children.items():
            if isinstance(val, Dict):
                items.append({
                    'name': key,
                    **val.serialize(app),
                })
            elif isinstance(val, dict):
                items.append({
                    'name': key,
                    **val
                })
            elif isinstance(val, list):
                for item in val:
                    items.append({
                        'name': key,
                        **item
                    })
            else:
                items.append({
                    'name': key,
                    self.VALUE_KEY: val,
                })
        return items


class PortsList(List):
    NAME = 'PortsList'
    VALUE_KEY = 'containerPort'


class Container(Dict):
    NAME = 'Container'

    volumeMounts: Dict
    env: Dict
    ports: Dict
    image: str
    command: Union[str, ListType[str]]

    def serialize(self, app=None):
        data = super().serialize(app)

        # Prepend default registry if image does not starts with "!"
        if data["image"].startswith("!"):
            data["image"] = data["image"][1:]
        elif app:
            data['image'] = '{registry}/{image}'.format(
                registry=app.registry,
                image=data['image'],
            )

        return data


class ContainersMixin:
    @staticmethod
    def _prepare_containers(containers):
        containers = containers or {}
        for key, val in containers.items():
            if 'volumeMounts' in val:
                val['volumeMounts'] = List(val['volumeMounts'])
            if 'env' in val:
                val['env'] = List(val['env'])
            if 'ports' in val:
                val['ports'] = PortsList(val['ports'])
            containers[key] = Container(val)

        return List(containers)


class KubernetesManifestMixin(JsonSerializable):
    __slots__ = ('name', 'metadata', 'spec')

    def __init__(self, metadata, annotations):
        metadata = metadata or {}
        metadata.setdefault('annotations', Dict(annotations or {}))
        self.metadata = Dict(metadata)
        self.spec = Dict()
        self.name = ''

    def serialize(self, app=None):
        res = {
            'apiVersion': self.api_version,
            'kind': self.obj_type.capitalize(),
            'metadata': self.metadata.serialize(app),
            'spec': self.spec.serialize(app)
        }

        return res


class Metadata(Dict):
    name: str
    annotations: Dict


class TemplateMetadata(Dict):
    name: str
    labels: Dict
    annotations: Dict


class TemplateSpec(Dict):
    volumes: List
    containers: DictType[str, Container]
    terminationGracePeriodSeconds: int


class DeploymentTemplate(Dict):
    metadata: TemplateMetadata
    spec: TemplateSpec


class DeploymentSpec(Dict):
    template: DeploymentTemplate
    replicas: int


class Deployment(ContainersMixin, KubernetesManifestMixin):
    obj_type = "deployment"
    api_version = "apps/v1"

    metadata: Metadata
    spec: DeploymentSpec

    def __init__(
            self, name='', containers: DictType[str, dict] = None,
            volumes: DictType[str, dict] = None, replicas=1, termination_grace_period=30,
            annotations: DictType[str, str] = None, metadata=None, labels=None,
            spec_annotations: DictType[str, str] = None,
    ):
        super().__init__(metadata, annotations)

        self.spec = DeploymentSpec(
            replicas=replicas,
            template=Dict(
                metadata=Dict(
                    labels=Dict(labels),
                    annotations=Dict(spec_annotations),
                ),
                spec=Dict(
                    volumes=List(volumes),
                    containers=self._prepare_containers(containers),
                    terminationGracePeriodSeconds=termination_grace_period,
                ),
            )
        )
        self.set_name(name)

    def set_name(self, name):
        """
        Sets name in:
        * metadata.name
        * metadata.annotations.name
        * spec.template.metadata.name
        * spec.template.metadata.labels.app
        """
        self.name = name
        self.metadata.name = name
        self.metadata.annotations.name = name
        self.spec.template.metadata.name = name
        self.spec.template.metadata.labels.app = name
        self.spec.selector.matchLabels.app = name


class JobTemplateSpec(Dict):
    restartPolicy: str
    terminationGracePeriodSeconds: int
    containers: DictType[str, Container]
    volumes: List


class JobTemplate(Dict):
    spec: JobTemplateSpec
    metadata: TemplateMetadata


class CronJobTemplateSpec(Dict):
    template: JobTemplate


class CronJobTemplate(Dict):
    spec: CronJobTemplateSpec
    metadata: Dict


class CronJobSpec(Dict):
    jobTemplate: CronJobTemplate
    schedule: str
    concurrencyPolicy: str


class CronJob(ContainersMixin, KubernetesManifestMixin):
    obj_type = "cronjob"
    api_version = "batch/v1beta1"

    metadata: Metadata
    spec: CronJobSpec

    def __init__(
            self, name='', schedule='', containers: DictType[str, dict] = None,
            termination_grace_period=30,
            restart_policy='Never',
            concurrency_policy='Allow',
            volumes: DictType[str, dict] = None,
            annotations=None, metadata=None, labels=None,
            spec_annotations=None,
    ):
        super().__init__(metadata, annotations)

        self.spec = CronJobSpec(
            schedule=schedule,
            concurrencyPolicy=concurrency_policy,
            jobTemplate=Dict(
                spec=Dict(
                    template=Dict(
                        metadata=Dict(
                            name=name,
                            labels=Dict(labels),
                            annotations=Dict(spec_annotations),
                        ),
                        spec=Dict(
                            volumes=List(volumes),
                            containers=self._prepare_containers(containers),
                            terminationGracePeriodSeconds=termination_grace_period,
                            restartPolicy=restart_policy,
                        ),
                    )
                )
            )
        )
        self.set_name(name)

    def set_name(self, name: str):
        """
        Sets name in:
        * spec.jobTemplate.spec.template.metadata.name
        * spec.jobTemplate.spec.template.metadata.labels.app
        """
        self.name = name
        self.metadata.name = name
        self.spec.jobTemplate.spec.template.metadata.name = name
        self.spec.jobTemplate.spec.template.metadata.labels.app = name

    def serialize(self, app=None):
        res = {
            'apiVersion': self.api_version,
            'kind': "CronJob",
            'metadata': self.metadata.serialize(app),
            'spec': self.spec.serialize(app)
        }

        return res


class JobSpec(Dict):
    template: JobTemplate
    backoffLimit: int
    parallelism: int


class Job(ContainersMixin, KubernetesManifestMixin):
    obj_type = "job"
    api_version = "batch/v1"

    metadata: Metadata
    spec: JobSpec

    def __init__(
            self, name='', containers: DictType[str, dict] = None,
            termination_grace_period=30,
            restart_policy='Never',
            volumes: DictType[str, dict] = None,
            annotations=None, metadata=None, labels=None,
            spec_annotations=None,
    ):
        super().__init__(metadata, annotations)

        self.spec = JobSpec(
            template=Dict(
                metadata=Dict(
                    name=name,
                    labels=Dict(labels),
                    annotations=Dict(spec_annotations),
                ),
                spec=Dict(
                    volumes=List(volumes),
                    containers=self._prepare_containers(containers),
                    terminationGracePeriodSeconds=termination_grace_period,
                    restartPolicy=restart_policy,
                ),
            )
        )
        self.set_name(name)

    def set_name(self, name: str):
        """
        Sets name in:
        * spec.template.metadata.name
        * spec.template.metadata.labels.app
        """
        self.name = name
        self.metadata.name = name
        self.spec.template.metadata.name = name
        self.spec.template.metadata.labels.app = name


class ServiceSpec(Dict):
    ports: List
    selector: Dict
    clusterIP: str
    loadBalancerIP: str
    type: str


class Service(KubernetesManifestMixin):
    obj_type = "service"
    api_version = "v1"

    metadata: Metadata
    spec: ServiceSpec

    def __init__(
            self, name='', ports: DictType[str, dict] = None, selector: DictType[str, str] = None,
            service_type='ClusterIP', load_balancer_ip=None, cluster_ip=None,
            annotations: DictType[str, str] = None, metadata=None,
    ):
        """
        :param selector: {'app': "foo"}
        :param ports: {'port_name': {'port': 1234, 'targetPort': 4321, 'protocol': 'TCP'}}
        """
        super().__init__(metadata, annotations)

        self.spec = ServiceSpec(
            type=service_type,
            ports=List(ports),
            selector=Dict(selector),
        )
        self.set_name(name)

        if load_balancer_ip:
            self.spec['loadBalancerIP'] = load_balancer_ip
        if cluster_ip:
            self.spec['clusterIP'] = cluster_ip

    def set_name(self, name):
        self.name = name
        self.metadata.name = name
