import versions


CONFIGMAP = {'PLACEHOLDER': 'PLACETAKER'}

DOCKER_FILES = []

K8S_OBJECTS = {
    "configmap": [
        {
            'name': 'test-config-map',
            'items': [
                {
                    'key': 'config',
                    'file': 'templates/configmap.conf',
                    'config': CONFIGMAP,
                }
            ]
        }
    ],
}
