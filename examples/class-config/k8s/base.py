import vindaloo
from vindaloo.objects import Deployment, Service

versions = vindaloo.app.versions
CONFIG = {
    'maintainer': "Avengers <avengers@domain.com>",
    'version': versions['avengers/adminserver'],
    'image_name': 'avengers/adminserver',
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
    name="avengers-adminserver",
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
        'avengers-adminserver': {
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
DEPLOYMENT_PRIVATE.name = "avengers-adminserver-private"
DEPLOYMENT_PRIVATE.metadata = {'name': DEPLOYMENT_PRIVATE.name}
DEPLOYMENT_PRIVATE.labels = {'app': DEPLOYMENT_PRIVATE.name}
DEPLOYMENT_PRIVATE.env = ENV_PRIVATE

SERVICE_PUBLIC = Service(
    name="avengers-adminserver",
    service_type="NodePort",
    selector={
        'app': "avengers-adminserver",
    },
    ports={
        'rpc': {'port': 3550, 'protocol': 'TCP'},
    }
)

SERVICE_PRIVATE = SERVICE_PUBLIC.clone()
SERVICE_PRIVATE.name = "avengers-adminserver-private"
SERVICE_PRIVATE.metadata = {'name': SERVICE_PRIVATE.name}
SERVICE_PRIVATE.selector['app'] = "avengers-adminserver-private"

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
