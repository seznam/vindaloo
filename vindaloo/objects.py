import copy
from typing import Optional


class JsonSerializable:
    NAME = "undefined"

    def serialize(self, app):
        raise NotImplementedError()

    def clone(self):
        return copy.deepcopy(self)

    def __str__(self):
        return str(f'{self.NAME}(**{self.serialize()})')


class Dict(JsonSerializable):
    __slots__ = ('childs',)

    NAME = 'Dict'

    def __init__(self, **kwargs):
        self.children = kwargs

    def serialize(self, app=None):
        return {
            key: val.serialize(app) if isinstance(val, Dict) else val
            for key, val in self.children.items()
        }

    def __getattr__(self, key):
        if key in self.children:
            return self.children[key]
        raise AttributeError(f'Key `{key}` not present')

    def __setattr__(self, key, val):
        if key in ('children', 'NAME'):
            super().__setattr__(key, val)
        else:
            self.children[key] = val

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __setitem__(self, key, value):
        self.children[key] = value

    def __deepcopy__(self, memo):
        return Dict(**copy.deepcopy(self.children, memo))


class List(Dict):
    NAME = 'List'

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
                    'value': val,
                })
        return items


class Container(Dict):
    NAME = 'Container'

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
    def _prepare_containers(self, containers):
        for key, val in containers.items():
            if 'volumeMounts' in val:
                val['volumeMounts'] = List(**val['volumeMounts'])
            if 'env' in val:
                val['env'] = List(**val['env'])
            containers[key] = Container(**val)

        return List(**containers)


class KubernetesManifestMixin(JsonSerializable):
    def __init__(self, name, metadata):
        self.name = name
        self.metadata = metadata or {
            'name': name,
        }

    def serialize(self, app):
        res = {
            'apiVersion': self.api_version,
            'kind': self.obj_type.capitalize(),
            'metadata': self.metadata,
            'spec': self.spec.serialize(app)
        }

        return res


class Deployment(ContainersMixin, KubernetesManifestMixin):
    obj_type = "deployment"
    api_version = "apps/v1"

    def __init__(
            self, name, containers,
            volumes=None, replicas=1, termination_grace_period=30,
            annotations=None, metadata=None, labels=None,
    ):
        super().__init__(name, metadata)
        labels = labels or {
            'app': name,
        }

        self.spec = Dict(
            replicas=replicas,
            selector=Dict(
                matchLabels=Dict(
                    app=name,
                ),
            ),
            template=Dict(
                metadata=Dict(
                    name=name,
                    labels=labels,
                    annotations=annotations,
                ),
                spec=Dict(
                    volumes=List(**volumes),
                    containers=self._prepare_containers(containers),
                    terminationGracePeriodSeconds=termination_grace_period,
                ),
            )
        )


class CronJob(ContainersMixin, KubernetesManifestMixin):
    obj_type = "cronjob"
    api_version = "batch/v1beta1"

    def __init__(
            self, name, schedule, containers,
            termination_grace_period=30,
            restart_policy='Never',
            concurrency_policy='Allow',
            volumes=None,
            annotations=None, metadata=None, labels=None,
    ):
        super().__init__(name, metadata)
        labels = labels or {
            'app': name,
        }

        self.spec = Dict(
            schedule=schedule,
            concurrencyPolicy=concurrency_policy,
            jobTemplate=Dict(
                spec=Dict(
                    template=Dict(
                        metadata=Dict(
                            name=name,
                            labels=labels,
                            annotations=annotations,
                        ),
                        spec=Dict(
                            volumes=List(**volumes),
                            containers=self._prepare_containers(containers),
                            terminationGracePeriodSeconds=termination_grace_period,
                            restartPolicy=restart_policy,
                        ),
                    )
                )
            )
        )

    def serialize(self, app):
        res = {
            'apiVersion': self.api_version,
            'kind': "CronJob",
            'metadata': self.metadata,
            'spec': self.spec.serialize(app)
        }

        return res


class Job(ContainersMixin, KubernetesManifestMixin):
    obj_type = "job"
    api_version = "batch/v1"

    def __init__(
            self, name, containers,
            termination_grace_period=30,
            restart_policy='Never',
            volumes=None,
            annotations=None, metadata=None, labels=None,
    ):
        super().__init__(name, metadata)
        labels = labels or {
            'app': name,
        }

        self.spec = Dict(
            template=Dict(
                metadata=Dict(
                    name=name,
                    labels=labels,
                    annotations=annotations,
                ),
                spec=Dict(
                    volumes=List(**volumes),
                    containers=self._prepare_containers(containers),
                    terminationGracePeriodSeconds=termination_grace_period,
                    restartPolicy=restart_policy,
                ),
            )
        )


class Service(KubernetesManifestMixin):
    obj_type = "service"
    api_version = "v1"

    def __init__(
            self, name, ports, selector,
            service_type='ClusterIP', load_balancer_ip=None, cluster_ip=None,
            annotations=None, metadata=None, labels=None,
    ):
        super().__init__(name, metadata)
        labels = labels or {
            'app': name,
        }

        self.metadata['annotations'] = annotations or {}

        self.spec = Dict(
            metadata=Dict(
                name=name,
            ),
            type=service_type,
            ports=List(**ports),
            selector=selector,
        )

        if load_balancer_ip:
            self.spec['loadBalancerIP'] = load_balancer_ip
        if cluster_ip:
            self.spec['clusterIP'] = cluster_ip
