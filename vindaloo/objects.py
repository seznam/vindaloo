import base64
import copy
from typing import Any, Union, Dict as DictType, List as ListType

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

    def serialize(self, *args, **kwargs):
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

    def serialize(self, *args, **kwargs):
        return {
            key: val.serialize(*args, **kwargs) if isinstance(val, Dict) else val
            for key, val in self.children.items()
        }

    def update(self, data):
        self.children.update(data)

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

    def __str__(self):
        return f'<Dict {self.children}>'

    def __repr__(self):
        return f'vindaloo.objects.Dict({self.children})'


class List(Dict):
    NAME = 'List'
    VALUE_KEY = 'value'

    def serialize(self, *args, **kwargs):
        items = []

        for key, val in self.children.items():
            if isinstance(val, Dict):
                items.append({
                    'name': key,
                    **val.serialize(*args, **kwargs),
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

    def serialize(self, *args, **kwargs):
        data = super().serialize(*args, **kwargs)

        # Prepend default registry if image does not starts with "!"
        if data["image"].startswith("!"):
            data["image"] = data["image"][1:]
        elif kwargs.get('app'):
            data['image'] = '{registry}/{image}'.format(
                registry=kwargs['app'].registry,
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
            if 'ports' in val and isinstance(val['ports'], dict):
                val['ports'] = PortsList(val['ports'])
            containers[key] = Container(val)

        return List(containers)


class KubernetesManifestMixin(JsonSerializable):
    __slots__ = ('name', 'metadata', 'spec')
    obj_type = ""
    api_version = ""

    def __init__(self, metadata, annotations):
        metadata = metadata or {}
        metadata.setdefault('annotations', Dict(annotations or {}))
        self.metadata = Dict(metadata)
        self.spec = Dict()
        self.name = ''

    def serialize(self, *args, **kwargs):
        res = {
            'apiVersion': self.api_version,
            'kind': self.obj_type.capitalize(),
            'metadata': self.metadata.serialize(*args, **kwargs),
            'spec': self.spec.serialize(*args, **kwargs)
        }

        return res


class Metadata(Dict):
    name: str
    annotations: Dict


class PodMetadata(Dict):
    name: str
    labels: Dict
    annotations: Dict


class PodSpec(Dict):
    volumes: List
    containers: DictType[str, Container]
    terminationGracePeriodSeconds: int
    restartPolicy: str


class Pod(Dict):
    metadata: PodMetadata
    spec: PodSpec


class ReplicaSet(Dict):
    template: Pod
    replicas: int


class Deployment(ContainersMixin, KubernetesManifestMixin):
    obj_type = "deployment"
    api_version = "apps/v1"

    metadata: Metadata
    spec: ReplicaSet

    def __init__(
            self, name='', containers: DictType[str, dict] = None,
            volumes: DictType[str, dict] = None, replicas=1, termination_grace_period=30,
            annotations: DictType[str, str] = None, metadata=None, labels=None,
            spec_annotations: DictType[str, str] = None,
    ):
        """
        :param annotations: Sets metadata.annotations in manifest
        :param spec_annotations: Sets spec.template.metadata.annotations in manifest
        :param termination_grace_period: Sets spec.template.spec.terminationGracePeriodSeconds in manifest
        """
        super().__init__(metadata, annotations)

        self.spec = ReplicaSet(
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


class CronJobTemplateSpec(Dict):
    template: Pod


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
        """
        :param annotations: Sets metadata.annotations in manifest
        :param spec_annotations: Sets spec.jobTemplate.spec.template.metadata.annotations in manifest
        """
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

    def serialize(self, *args, **kwargs):
        res = {
            'apiVersion': self.api_version,
            'kind': "CronJob",
            'metadata': self.metadata.serialize(*args, **kwargs),
            'spec': self.spec.serialize(*args, **kwargs)
        }

        return res


class JobSpec(Dict):
    template: Pod
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
        """
        :param annotations: Sets metadata.annotations in manifest
        :param spec_annotations: Sets spec.template.metadata.annotations in manifest
        """
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


class ConfigMap(KubernetesManifestMixin):
    obj_type = 'configmap'
    api_version = 'v1'
    __slots__ = (
        'name', 'metadata', 'spec', 'data', 'binary_data', 'immutable',
    )

    def __init__(
        self,
        name: str,
        data: DictType[str, Union[None, int, float, str, dict]] = None,
        binary_data: DictType[str, Union[bytes, dict]] = None,
        immutable: bool = False,
        annotations: DictType[str, str] = None,
        metadata: DictType[str, Any] = None,
    ):
        super().__init__(metadata, annotations)
        self.set_name(name)
        self.data = data or {}
        self.binary_data = binary_data or {}
        self.immutable = immutable

    def set_name(self, name):
        self.name = name
        self.metadata.name = name

    @staticmethod
    def _binary_value_prep(value: bytes) -> str:
        return base64.encodebytes(value).decode()

    def _file_prep(self, app, filename: str, config: DictType, is_binary: bool) -> str:
        if not filename:
            raise ValueError(f'Value of a config key can be either atomic value or dict with a `file` key.')

        if is_binary:
            with open(f'k8s/{filename}', 'br') as file:
                return self._binary_value_prep(file.read())
        else:
            temp_file = app.create_file(filename, config, no_edit=True)
            file_content = temp_file.read()
            temp_file.close()
            return file_content.decode('utf-8')

    def prepare_data(self, data: DictType[str, Any], app, is_binary: bool = False) -> DictType[str, str]:
        new_data = {}
        for key, value in data.items():
            if isinstance(value, dict):
                new_data[key] = self._file_prep(
                    app,
                    value.get('file'),
                    value.get('config', {}),
                    is_binary,
                )
            else:
                if is_binary:
                    value = self._binary_value_prep(value)
                new_data[key] = str(value)
        return new_data

    def serialize(self, *args, **kwargs):
        keys_intersection = set(self.data.keys()) & set(self.binary_data.keys())
        if keys_intersection:
            raise ValueError(f"`data` and `binary_data` cannot contain same keys: {keys_intersection}")

        res = {
            'apiVersion': self.api_version,
            'kind': 'ConfigMap',
            'metadata': self.metadata.serialize(*args, **kwargs),
        }
        if self.data:
            res['data'] = self.prepare_data(self.data, kwargs.get('app'))
        if self.binary_data:
            res['binaryData'] = self.prepare_data(self.binary_data, kwargs.get('app'), is_binary=True)
        if self.immutable:
            res['immutable'] = True

        return res
