import copy
import json


class JsonSerializable:
    def to_json(self, app):
        raise NotImplementedError()

    def clone(self):
        return copy.deepcopy(self)


class PrepareDataMixin:
    def prepare_container_data(self, data, app):

        # Prepend default registry if image does not starts with "!"
        if data["image"].startswith("!"):
            data["image"] = data["image"][1:]
        else:
            data['image'] = '{registry}/{image}'.format(
                registry=app.registry,
                image=data['image'],
            )

        for key, val in data.get('env', {}).items():
            if not isinstance(val, dict):
                data['env'][key] = {'value': val}

        data['env'] = [
            {
                'name': key,
                **val,
            } for key, val in data.get('env', {}).items()
        ]

        mounts = []
        for volume_name, mount in data.get('volumeMounts', {}).items():
            if isinstance(mount, dict):
                mounts.append({
                    'name': volume_name,
                    **mount
                })
            else:  # we have more mounts of one volume
                for one_mount in mount:
                    mounts.append({
                        'name': volume_name,
                        **one_mount
                    })
        data['volumeMounts'] = mounts

        return data


class Deployment(JsonSerializable, PrepareDataMixin):
    obj_type = "deployment"
    api_version = "extensions/v1beta1"

    def __init__(
            self, name, containers,
            volumes=None, replicas=1, termination_grace_period=30,
            annotations=None, metadata=None, labels=None,
            **kwargs
    ):
        self.name = name
        self.replicas = replicas
        self.annotations = annotations or {}
        self.containers = containers
        self.termination_grace_period = termination_grace_period
        self.volumes = volumes or {}
        self.metadata = metadata or {
            'name': self.name,
        }
        self.labels = labels or {
            'app': self.name,
        }
        self.additional_params = kwargs

    def prepare_container_data(self, data, app):
        data = super().prepare_container_data(data, app)
        data['ports'] = [
            {'containerPort': port, 'name': name}
            for name, port in data['ports'].items()
        ]
        return data

    def to_json(self, app):
        res = {
            'apiVersion': self.api_version,
            'kind': self.obj_type.capitalize(),
            'metadata': self.metadata,
            'spec': {
                'replicas': self.replicas,
                'template': {
                    'metadata': {
                        'name': self.name,
                        'labels': self.labels,
                        'annotations': self.annotations,
                    },
                    'spec': {
                        'volumes': [
                            {
                                'name': key,
                                **val
                            } for key, val in self.volumes.items()
                        ],
                        'containers': [
                            {
                                'name': key,
                                **self.prepare_container_data(val, app)
                            } for key, val in self.containers.items()
                        ],
                        'terminationGracePeriodSeconds': self.termination_grace_period,
                    }
                }
            }
        }

        res.update(self.additional_params)

        return json.dumps(res, indent=4)


class CronJob(JsonSerializable, PrepareDataMixin):
    obj_type = "cronjob"
    api_version = "batch/v1beta1"

    def __init__(
            self, name, schedule, containers,
            termination_grace_period=30,
            restart_policy='Never',
            concurrency_policy='Allow',
            volumes=None,
            annotations=None, metadata=None, labels=None,
            **kwargs
    ):
        self.name = name
        self.schedule = schedule
        self.termination_grace_period = termination_grace_period
        self.restart_policy = restart_policy
        self.concurrency_policy = concurrency_policy
        self.annotations = annotations or {}
        self.containers = containers
        self.volumes = volumes or {}
        self.metadata = metadata or {
            'name': self.name,
        }
        self.labels = labels or {
            'app': self.name,
        }
        self.additional_params = kwargs

    def to_json(self, app):
        res = {
            'apiVersion': self.api_version,
            'kind': "CronJob",
            'metadata': self.metadata,
            'spec': {
                'schedule': self.schedule,
                'concurrencyPolicy': self.concurrency_policy,
                'jobTemplate': {
                    'spec': {
                        'template': {
                            'metadata': {
                                'name': self.name,
                                'labels': self.labels,
                                'annotations': self.annotations,
                            },
                            'spec': {
                                'restartPolicy': self.restart_policy,
                                'terminationGracePeriodSeconds': self.termination_grace_period,
                                'volumes': [
                                    {
                                        'name': key,
                                        **val
                                    } for key, val in self.volumes.items()
                                ],
                                'containers': [
                                    {
                                        'name': key,
                                        **self.prepare_container_data(val, app)
                                    } for key, val in self.containers.items()
                                ]
                            }
                        }
                    }
                }
            }
        }

        res.update(self.additional_params)

        return json.dumps(res, indent=4)


class Job(JsonSerializable, PrepareDataMixin):
    obj_type = "job"
    api_version = "batch/v1"

    def __init__(
            self, name, containers,
            termination_grace_period=30,
            restart_policy='Never',
            volumes=None,
            annotations=None, metadata=None, labels=None,
            backoff_limit=6,
            **kwargs
    ):
        self.name = name
        self.termination_grace_period = termination_grace_period
        self.restart_policy = restart_policy
        self.annotations = annotations or {}
        self.containers = containers
        self.volumes = volumes or {}
        self.metadata = metadata or {
            'name': self.name,
        }
        self.labels = labels or {
            'app': self.name,
        }
        self.additional_params = kwargs
        self.backoff_limit = backoff_limit

    def to_json(self, app):
        res = {
            'apiVersion': self.api_version,
            'kind': self.obj_type.capitalize(),
            'metadata': self.metadata,
            'spec': {
                'template': {
                    'metadata': {
                        'name': self.name,
                        'labels': self.labels,
                        'annotations': self.annotations,
                    },
                    'spec': {
                        'restartPolicy': self.restart_policy,
                        'volumes': [
                            {
                                'name': key,
                                **val
                            } for key, val in self.volumes.items()
                        ],
                        'containers': [
                            {
                                'name': key,
                                **self.prepare_container_data(val, app)
                            } for key, val in self.containers.items()
                        ],
                        'terminationGracePeriodSeconds': self.termination_grace_period,
                    }
                },
                'backoffLimit': self.backoff_limit,
            }
        }

        res.update(self.additional_params)

        return json.dumps(res, indent=4)


class Service(JsonSerializable):
    obj_type = "service"
    api_version = "v1"

    def __init__(
            self, name, ports, selector,
            service_type='ClusterIP', load_balancer_ip=None, cluster_ip=None,
            annotations=None, metadata=None, labels=None,
            **kwargs
    ):
        self.name = name
        self.ports = ports or {}
        self.selector = selector
        self.service_type = service_type
        self.load_balancer_ip = load_balancer_ip
        self.cluster_ip = cluster_ip
        self.annotations = annotations
        self.metadata = metadata or {
            'name': self.name,
        }
        self.metadata['annotations'] = self.annotations or {}
        self.additional_params = kwargs

    def to_json(self, app):
        res = {
            'apiVersion': self.api_version,
            'kind': self.obj_type.capitalize(),
            'metadata': self.metadata,
            'spec': {
                'type': self.service_type,
                'ports': [
                    {
                        'name': name,
                        **val,
                    }
                    for name, val in self.ports.items()],
                'selector': self.selector,
            }
        }

        if self.load_balancer_ip:
            res['spec']['loadBalancerIP'] = self.load_balancer_ip
        if self.cluster_ip:
            res['spec']['clusterIP'] = self.cluster_ip

        res.update(self.additional_params)

        return json.dumps(res, indent=4)
