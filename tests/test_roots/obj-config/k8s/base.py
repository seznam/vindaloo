import versions
from vindaloo.objects import Deployment, Service, CronJob, Job

CONFIG = {
    'maintainer': "Foo <test@foo.com>",
    'version': versions['test/foo'],
    'image_name': 'test/foo',
}

DEPLOYMENT = Deployment(
    name="foo",
    replicas=2,
    volumes={
        'localconfig': {
            'secret': {
                'secretName': "local-conf",
            }
        },
        'cert': {
            'secret': {
                'secretName': "cert",
            }
        },
    },
    containers={
        'foo': {
            'image': "{}:{}".format(CONFIG['image_name'], CONFIG['version']),
            'ports': {
                'proxy': 5001,
            },
            'env': {
                'ENV': "stable",
                'DB_PASSWORD': {
                    'valueFrom': {
                        'secretKeyRef': {
                            'name': 'db-master',
                            'key': 'password',
                        }
                    }
                },
            },
            'volumeMounts': {
                'cert': [
                    {
                        'mountPath': "/cert.pem",
                        'subPath': "tls.crt",
                    },
                    {
                        'mountPath': "/key.pem",
                        'subPath': "tls.key",
                    },
                ],
            },
            'livenessProbe': {
                'initialDelaySeconds': 30,
                'periodSeconds': 30,
                'timeoutSeconds': 10,
                'httpGet': {
                    'path': "/",
                    'port': 5001,
                }
            },
        },
    },
    annotations={"deploy-cluster": "cluster1"},
    spec_annotations={"log-retention": "3w"}
)
DEPLOYMENT.spec.something = {'foo': 'boo'}

CRONJOB = CronJob(
    name="foo",
    schedule="0 0 * * *",
    volumes={
        'localconfig': {
            'secret': {
                'secretName': "local-conf",
            }
        }
    },
    containers={
        'foo': {
            'image': "!registry.hub.docker.com/library/busybox:latest",
            'command': ['echo', 'x'],
            'env': {
                'ENV': "stable",
                'DB_PASSWORD': {
                    'valueFrom': {
                        'secretKeyRef': {
                            'name': 'db-master',
                            'key': 'password',
                        }
                    }
                },
            },
            'volumeMounts': {
                'localconfig': {
                    'mountPath': "/app.local.conf",
                    'subPath': "app.local.conf",
                },
            },
        },
    },
)

JOB1 = Job(
    name="foo",
    volumes={
        'localconfig': {
            'secret': {
                'secretName': "local-conf",
            }
        }
    },
    containers={
        'foo': {
            'image': "{}:{}".format(CONFIG['image_name'], CONFIG['version']),
            'command': ['echo', 'x'],
            'env': {
                'ENV': "stable",
                'DB_PASSWORD': {
                    'valueFrom': {
                        'secretKeyRef': {
                            'name': 'db-master',
                            'key': 'password',
                        }
                    }
                },
            },
        },
    },
)

JOB2 = JOB1.clone()
JOB2.name = 'bar'
JOB2.spec.template.metadata.name = 'bar'
JOB2.spec.template.spec.containers['foo']['command'] = ['echo', 'y']

SERVICE = Service(
    name="foo",
    service_type="NodePort",
    selector={
        'app': "foo",
    },
    ports={
        'http': {'port': 5001, 'protocol': 'TCP'},
    }
)

LOADBALANCER = Service(
    name="foo-labrador",
    selector={
        'app': "foo",
    },
    ports={
        'http': {'port': 5001, 'targetPort': 5001, 'protocol': 'TCP'},
    },
    cluster_ip="None",
)

DOCKER_FILES = [
    {
        'context_dir': "..",
        'config': CONFIG,
        'template': "Dockerfile",
    },
]

K8S_OBJECTS = {
    "deployment": [DEPLOYMENT],
    "cronjob": [CRONJOB],
    "job": [JOB1, JOB2],
    "service": [
        SERVICE,
        LOADBALANCER,
    ]
}
