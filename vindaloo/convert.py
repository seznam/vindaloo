import json
import logging

import vindaloo

from .objects import (
    JsonSerializable,
    Deployment,
    Service,
)

TAB = "    "


def get_obj_repr_from_dict(data) -> JsonSerializable:
    kind = data.get('kind')

    if kind == 'Deployment':
        res = get_deployment_obj_repr_from_dict(data)
    elif kind == 'Service':
        res = get_service_obj_repr_from_dict(data)
    else:
        raise Exception(f"Kind '{kind}' is not supported yet.")

    content = f"""
import vindaloo
from vindaloo.objects import {kind}

versions = vindaloo.app.versions

{kind.upper()} = {res}

K8S_OBJECTS = {{
    "{kind.lower()}": [{kind.upper()}],
}}
"""
    return content


def get_deployment_obj_repr_from_dict(data) -> Deployment:
    metadata = data.get('metadata', {})
    metadata.get('labels', {}).pop('app', None)
    name = metadata.pop('name', None)

    template = data.get('spec', {}).get('template', {})
    template_metadata = template.get('metadata', {})
    template_metadata.get('labels', {}).pop('app')

    template_spec = template.get('spec', {})

    containers = create_dict_from_named_list(template_spec.get('containers', []))
    containers_string = "{\n"

    for name, container in containers.items():
        image = ''
        if container.get('image'):
            try:
                v = vindaloo.vindaloo.Vindaloo()
                v._import_envs_config()
                container['image'] = v._strip_image_name(container['image'])
            except Exception as ex:
                logging.warning(str(ex))
            image, version = container['image'].split(':')
            add_version(image, version)

        dict_ports = {}
        for port in container.get('ports', []):
            if port.get('name'):
                dict_ports[port['name']] = port
                port.pop('name')

        containers_string += TAB * 2 + f"'{name}': {{\n"
        containers_string += TAB * 3 + f"""'image': "{image}:" + versions['{image}'],\n"""
        containers_string += TAB * 3 + f"'ports': {dict_ports or container.get('ports', [])},\n"
        containers_string += TAB * 3 + f"'env': {create_dict_from_name_value_list(container.get('env', []))},\n"
        containers_string += TAB * 2 + "},\n"
    containers_string += TAB + "}"

    termination = template_spec.get('terminationGracePeriodSeconds', 30)

    res = f"""Deployment(
    name="{name}",
    replicas={data.get('spec', {}).get('replicas')},
    containers={containers_string or None},
    volumes=None,
    annotations=None, 
    metadata={metadata or None}, 
    labels={template_metadata.get('labels') or None},
    spec_annotations={template_metadata.get('annotations') or None},
    termination_grace_period={termination},
)"""
    return res


def get_service_obj_repr_from_dict(data) -> Service:
    pass


def create_dict_from_named_list(data):
    res = {}
    for item in data:
        name = item.pop('name')
        res[name] = item
    return res


def create_dict_from_name_value_list(data):
    res = {}
    for item in data:
        name = item.pop('name')
        res[name] = item.get('value')
    return res


def add_version(image, version):
    file = f'{vindaloo.vindaloo.CONFIG_DIR}/versions.json'

    with open(file, 'r+') as fp:
        versions = json.load(fp)
        versions[image] = version
        fp.seek(0)
        json.dump(versions, fp)
