import versions
from vindaloo.objects import Deployment, Service

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
        }
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
)

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
    "service": [
        SERVICE,
        LOADBALANCER,
    ]
}
