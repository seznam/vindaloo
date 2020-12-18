import vindaloo

versions = vindaloo.app.versions

MAINTAINER = "Daniel Milde <daniel.milde@firma.seznam.cz>"

CONFIG_WEB = {
    'maintainer': MAINTAINER,
    'version': versions['avengers/web'],
    'image_name': 'avengers/web',
    'https_proxy': "http://proxy.com:3128",
}
CONFIG_PROXY = {
    'maintainer': MAINTAINER,
    'version': versions['avengers/web-proxy'],
    'image_name': 'avengers/web-proxy',
}
CONFIG_OUTAGE = {
    'maintainer': MAINTAINER,
    'version': versions['avengers/web-outage'],
    'image_name': 'avengers/web-outage',
}

DEPLOYMENT_ADMINWEB = {
    'replicas': 2,
    'ident_label': "avengers-web",
    'image_web': "{}:{}".format(CONFIG_WEB['image_name'], CONFIG_WEB['version']),
    'image_proxy': "{}:{}".format(CONFIG_PROXY['image_name'], CONFIG_PROXY['version']),
    'env': [
        {
            'key': 'ENVIRONMENT',
            'val': "avengers-stable"
        },
        {
            'key': 'PORT',
            'val': "8001"
        },
        {
            'key': 'http_proxy',
            'val': "http://proxy:3128",
        },
        {
            'key': 'https_proxy',
            'val': "http://proxy:3128",
        },
    ],
    'port_web': "8001",
    'port_proxy': "8000",
}

DEPLOYMENT_OUTAGE = {
    'replicas': 1,
    'ident_label': "avengers-web-outage",
    'image': "{}:{}".format(CONFIG_OUTAGE['image_name'], CONFIG_OUTAGE['version']),
    'port': "8000",
}

SERVICE = {
    'app_name': "avengers-web",
    'ident_label': "avengers-web",
    'ports': [
        {'port': 8000, 'name': 'http'},
    ]
}

DOCKER_FILES = [
    {
        'context_dir': "..",
        'config': CONFIG_WEB,
        'template': "Dockerfile.web",
        'includes': {
            'base_image': "../k8s-includes/BaseImage.include",
        },
        'pre_build_msg': """Prosim nejdriv spust (v Dockeru):

make clean compile-messages
cd web; make rights compile-production
"""
    },
    {
        'context_dir': "..",
        'config': CONFIG_PROXY,
        'template': "Dockerfile.proxy",
        'pre_build_msg': """Prosim nejdriv spust (v Dockeru):

make clean
cd web; make compile-production
"""
    },
    {
        'context_dir': "..",
        'config': CONFIG_OUTAGE,
        'template': "Dockerfile.outage",
    }
]

K8S_OBJECTS = {
    "deployment": [
        {
            'config': DEPLOYMENT_ADMINWEB,
            'template': "deployment.yaml",
        },
        {
            'config': DEPLOYMENT_OUTAGE,
            'template': "deployment.outage.yaml",
        },
    ],
    "service": [
        {
            'config': SERVICE,
            'template': "service.yaml",
        },
    ]
}
