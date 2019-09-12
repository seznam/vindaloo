import versions

CONFIG = {
    'maintainer': "Test Test <test.test@firma.seznam.cz>",
    'version': versions['test/foo'],
    'image_name': 'foo-registry.com/test/foo',
}

CONFIG_SECOND = {
    'maintainer': "Test Test <test.test@firma.seznam.cz>",
    'version': versions['test/bar'],
    'image_name': 'foo-registry.com/test/bar',
}

DEPLOYMENT = {
    'replicas': 1,
    'ident_label': "foobar",
    'image': "{}:{}".format(CONFIG['image_name'], CONFIG['version']),
    'image_second': "{}:{}".format(CONFIG_SECOND['image_name'], CONFIG_SECOND['version']),
    'spec_annotations': [],
}

DOCKER_FILES = [
    {
        'config': CONFIG,
        'template': "Dockerfile",
        'includes': {
            'from': "k8s/templates/from.include",
        }
    },
    {
        'config': CONFIG_SECOND,
        'template': "Dockerfile2",
    },
]

K8S_OBJECTS = {
    "deployment": [
        {
            'config': DEPLOYMENT,
            'template': "deployment.yaml",
        },
    ],
}
