import copy
from typing import Optional


class JsonSerializable:
    NAME: Optional[str] = None

    def serialize(self, app):
        raise NotImplementedError()

    def clone(self):
        return copy.deepcopy(self)

    def __str__(self):
        return str(f'{self.NAME}(**{self.serialize()})')


class DictSerializable(JsonSerializable):
    __slots__ = ('childs',)

    NAME = 'DictSerializable'

    def __init__(self, **kwargs):
        self.childs = kwargs

    def serialize(self, app=None):
        return {
            key: val.serialize(app) if isinstance(val, DictSerializable) else val
            for key, val in self.childs.items()
        }

    def __getattr__(self, key):
        if key in self.childs:
            return self.childs[key]
        raise AttributeError(f'Key `{key}` not present')

    def __setattr__(self, key, val):
        if key in ('childs', 'NAME'):
            super().__setattr__(key, val)
        else:
            self.childs[key] = val

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __setitem__(self, key, value):
        self.childs[key] = value

    def __deepcopy__(self, memo):
        return DictSerializable(**copy.deepcopy(self.childs, memo))


class ListSerializable(DictSerializable):
    NAME = 'ListSerializable'

    def serialize(self, app=None):
        items = []

        for key, val in self.childs.items():
            if isinstance(val, DictSerializable):
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


class Container(DictSerializable):
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


class PrepareContainersMixin:
    def _prepare_containers(self, containers):
        for key, val in containers.items():
            if 'volumeMounts' in val:
                val['volumeMounts'] = ListSerializable(**val['volumeMounts'])
            if 'env' in val:
                val['env'] = ListSerializable(**val['env'])
            containers[key] = Container(**val)

        return ListSerializable(**containers)


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


class Deployment(PrepareContainersMixin, KubernetesManifestMixin):
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

        self.spec = DictSerializable(
            replicas=replicas,
            selector=DictSerializable(
                matchLabels=DictSerializable(
                    app=name,
                ),
            ),
            template=DictSerializable(
                metadata=DictSerializable(
                    name=name,
                    labels=labels,
                    annotations=annotations,
                ),
                spec=DictSerializable(
                    volumes=ListSerializable(**volumes),
                    containers=self._prepare_containers(containers),
                    terminationGracePeriodSeconds=termination_grace_period,
                ),
            )
        )


class CronJob(PrepareContainersMixin, KubernetesManifestMixin):
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

        self.spec = DictSerializable(
            schedule=schedule,
            concurrencyPolicy=concurrency_policy,
            jobTemplate=DictSerializable(
                spec=DictSerializable(
                    template=DictSerializable(
                        metadata=DictSerializable(
                            name=name,
                            labels=labels,
                            annotations=annotations,
                        ),
                        spec=DictSerializable(
                            volumes=ListSerializable(**volumes),
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


class Job(PrepareContainersMixin, KubernetesManifestMixin):
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

        self.spec = DictSerializable(
            template=DictSerializable(
                metadata=DictSerializable(
                    name=name,
                    labels=labels,
                    annotations=annotations,
                ),
                spec=DictSerializable(
                    volumes=ListSerializable(**volumes),
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

        self.spec = DictSerializable(
            metadata=DictSerializable(
                name=name,
            ),
            type=service_type,
            ports=ListSerializable(**ports),
            selector=selector,
        )

        if load_balancer_ip:
            self.spec['loadBalancerIP'] = load_balancer_ip
        if cluster_ip:
            self.spec['clusterIP'] = cluster_ip
