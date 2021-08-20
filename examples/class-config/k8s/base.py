import vindaloo
from vindaloo.objects import Deployment, Service

versions = vindaloo.app.versions

CONFIG = {
    'maintainer': "Avengers <avengers@domain.com>",
    'version': versions['avengers/server'],
    'image_name': 'avengers/server',
}

ENV_PUBLIC = {
    'ENVIRONMENT': "avengers-stable",
    'WEB_CONCURRENCY': "15",
    'VERSION': CONFIG['version'],
}

ENV_PRIVATE = {
    **ENV_PUBLIC,
    'WEB_CONCURRENCY': "40",
    'REGISTER_PRIVATE_METHODS': "1",
}

DEPLOYMENT_PUBLIC = Deployment(
    name="avengers-server",
    replicas=4,
    annotations={
        'team': "avengers@domain.com",
    },
    volumes={
        'localconfig': {
            'secret': {
                'secretName': "avengers-local-conf",
            }
        }
    },
    containers={
        'avengers-server': {
            'image': "{}:{}".format(CONFIG['image_name'], CONFIG['version']),
            'ports': {
                'proxy': 3550,
            },
            'env': ENV_PUBLIC,
            'volumeMounts': {
                'localconfig': {
                    'mountPath': "/local.conf",
                    'subPath': "local.conf",
                }
            },
            'lifecycle': {
                'preStop': {
                    'exec': {
                        'command': ["/bin/sh", "-c", "sleep 20; kill -s TERM `cat /gunicorn.pid`"]
                    }
                }
            },
            'livenessProbe': {
                'initialDelaySeconds': 15,
                'periodSeconds': 10,
                'timeoutSeconds': 3,
                'httpGet': {
                    'path': "/selfcheck",
                    'port': 3550,
                }
            },
            'readinessProbe': {
                'initialDelaySeconds': 15,
                'periodSeconds': 10,
                'timeoutSeconds': 3,
                'httpGet': {
                    'path': "/ready",
                    'port': 3550,
                }
            },
            'resources': {
                'limits': {
                    'cpu': "6",
                    'memory': "6000Mi",
                },
                'requests': {
                    'cpu': "3",
                    'memory': "3000Mi",
                }
            },
        },
    },
)

DEPLOYMENT_PRIVATE = DEPLOYMENT_PUBLIC.clone()
DEPLOYMENT_PRIVATE.set_name("avengers-server-private")
DEPLOYMENT_PRIVATE.spec.template.spec.containers['avengers-server']['env'] = ENV_PRIVATE

SERVICE_PUBLIC = Service(
    name="avengers-server",
    service_type="NodePort",
    selector={
        'app': "avengers-server",
    },
    ports={
        'rpc': {'port': 3550, 'protocol': 'TCP'},
    }
)

SERVICE_PRIVATE = SERVICE_PUBLIC.clone()
SERVICE_PRIVATE.set_name("avengers-server-private")

DOCKER_FILES = [
    {
        'context_dir': "..",
        'config': CONFIG,
        'template': "Dockerfile",
        'includes': {
            'base_image': "../k8s-includes/BaseImage.include",
        },
    },
]

K8S_OBJECTS = {
    "deployment": [
        DEPLOYMENT_PUBLIC,
        DEPLOYMENT_PRIVATE,
    ],
    "service": [
        SERVICE_PUBLIC,
        SERVICE_PRIVATE,
    ]
}
