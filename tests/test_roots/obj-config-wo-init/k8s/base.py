import vindaloo
from vindaloo import Container, CronJob, Deployment, Job, List, Service

versions = vindaloo.app.versions

CONFIG = {
    'maintainer': "Foo <test@foo.com>",
    'version': versions['test/foo'],
    'image_name': 'test/foo',
}

DEPLOYMENT = Deployment()
DEPLOYMENT.set_name("foo")
DEPLOYMENT.spec.template.spec.volumes = List({
    'localconfig': {'secret': {'secretName': "local-conf"}},
    'cert': {'secret': {'secretName': "cert"}},
})

CONTAINER = Container()
CONTAINER.image = f"{CONFIG['image_name']}:{CONFIG['version']}"
CONTAINER.volumeMounts = List({
    'cert': [
        {'mountPath': "/cert.pem", 'subPath': "tls.crt"},
        {'mountPath': "/key.pem", 'subPath': "tls.key"},
    ],
})
CONTAINER.env = List({
    'ENV': 'stable',
})
CONTAINER.ports = List({
    'proxy': {
        'containerPort': 5001
    },
    'server': {
        'containerPort': 5000,
        'protocol': 'UDP',
    }
})

DEPLOYMENT.spec.template.spec.containers = List({'foo': CONTAINER})
DEPLOYMENT.spec.template.metadata.annotations['log-retention'] = '3w'
DEPLOYMENT.metadata.annotations['deploy-cluster'] = 'cluster2'
DEPLOYMENT.spec.something.foo = 'boo'

CRONJOB_CONTAINER = Container()
CRONJOB_CONTAINER.image = "!registry.hub.docker.com/library/busybox:latest"
CRONJOB_CONTAINER.command = ['echo', 'x']
CRONJOB_CONTAINER.env = List({
    'ENV': "stable",
    'DB_PASSWORD': {
        'valueFrom': {
            'secretKeyRef': {
                'name': 'db-master',
                'key': 'password',
            }
        }
    },
})
CRONJOB_CONTAINER.volumeMounts = List({
    'localconfig': {
        'mountPath': "/app.local.conf",
        'subPath': "app.local.conf",
    },
})

CRONJOB = CronJob()
CRONJOB.set_name("foo")
CRONJOB.spec.schedule = "0 0 * * *"
CRONJOB.spec.jobTemplate.spec.template.spec.volumes = List({
    'localconfig': {
        'secret': {
            'secretName': "local-conf",
        }
    }
})
CRONJOB.spec.jobTemplate.spec.template.spec.containers = List({'foo': CRONJOB_CONTAINER})

JOB_CONTAINER = Container()
JOB_CONTAINER.image = f"{CONFIG['image_name']}:{CONFIG['version']}"
JOB_CONTAINER.command = ['echo', 'x']
JOB_CONTAINER.env = List({
    'ENV': "stable",
    'DB_PASSWORD': {
        'valueFrom': {
            'secretKeyRef': {
                'name': 'db-master',
                'key': 'password',
            }
        }
    },
})

JOB1 = Job()
JOB1.set_name("foo")
JOB1.spec.template.spec.volumes = List({
    'localconfig': {
        'secret': {
            'secretName': "local-conf",
        }
    }
})
JOB1.spec.template.spec.containers = List({'foo': JOB_CONTAINER})

JOB2 = JOB1.clone()
JOB2.set_name('bar')
JOB2.spec.template.spec.containers['foo']['command'] = ['echo', 'y']

SERVICE = Service()
SERVICE.set_name("foo")
SERVICE.spec.type = "NodePort"
SERVICE.spec.selector = {'app': "foo"}
SERVICE.spec.ports = List({
    'http': {'port': 5001, 'targetPort': 5001, 'protocol': 'TCP'},
})
SERVICE.metadata.annotations.loadbalancer = "enabled"

DOCKER_FILES = [
    {
        'context_dir': "..",
        'config': CONFIG,
        'template': "Dockerfile",
    },
]

K8S_OBJECTS = {
    'deployment': [DEPLOYMENT],
    'cronjob': [CRONJOB],
    'job': [JOB1, JOB2],
    'service': [
        SERVICE,
    ]
}
