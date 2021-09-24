import vindaloo
from vindaloo.objects import ConfigMap

versions = vindaloo.app.versions


CONTEXT = {'variable_1': 'This value depends on the selected environment.'}

DOCKER_FILES = []

CONFIG_MAP = ConfigMap(
    name='test-config-map',
    metadata={
        'labels': {'custom-labels': '123'},
        'annotations': {'custom-annotations': '...'},
    },
    immutable=True,
    data={
        'simple_config_key': 123,
        'file_config_key': {
            'file': 'templates/file_config.conf',
            'config': CONTEXT,
        },
    },
    binary_data={
        'simple_binary_key': b'\x76\x69\x6b\x79',
        'binary_file_config_key': {
            'file': 'templates/binary_config.conf',
        },
    },
)

K8S_OBJECTS = {
    "configmap": [CONFIG_MAP],
}
