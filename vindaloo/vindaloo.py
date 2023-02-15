#!/usr/bin/python3

import argparse
import base64
import imp
import shutil
from importlib import import_module
import json
import os
import ssl
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Set, BinaryIO, Sequence
import urllib.request

import argcomplete
import chevron

from .convert import get_obj_repr_from_dict
from .examples import (
    EXAMPLE_VINDALOO_CONF,
    EXAMPLE_BASE,
    EXAMPLE_DEV,
    EXAMPLE_DOCKERFILE,
    EXAMPLE_DEPLOYMENT,
    EXAMPLE_SERVICE,
)
from .objects import JsonSerializable
from .utils import NamespaceWithDefaultValue

DO_NOT_NEED_CONFIG_FILE = ('init', 'completion', 'version')
DO_NOT_NEED_K8S_DIR = ('edit-secret',)

NONE = "base"
K8S_OBJECT_TYPES = [
    "configmap", "secret", "podpreset", "deployment", "service", "ingres", "cronjob", "job"
]
K8S_OBJECT_TYPES_YAML_PREFIX = {
    "configmap": "1",
    "secret": "2",
    "podpreset": "3",
    "deployment": "4",
    "service": "5",
    "ingres": "6",
    "cronjob": "7",
    "job": "8",
}
SUCCESS_REPLY = ("Y", "y", "a", "A")
ENVS_CONFIG_NAME = 'vindaloo_conf'
NEEDS_K8S_LOGIN = ('versions', 'deploy', 'build-push-deploy', 'edit-secret')
CONFIG_DIR = 'k8s'
GIT_HASH_PLACEHOLDER = '{{git}}'
CHECK_VERSION_URL = 'https://raw.githubusercontent.com/seznam/vindaloo/master/version.json'

VERSION = '4.4.0'


class RefreshException(Exception):
    pass


class Vindaloo:
    """
    Tool which should make docker and k8s stuff easier.
    """

    def __init__(self):
        self.envs_config_module = None  # konfigurace prostredi (clustery, namespacy)
        self.config_module = None  # konfigurace aktualne vybraneho prostredi (Dockerfily, deploymenty, porty, ...)
        self.args = None
        self.changed_secrets = {}  # Secrety naplanovane ke zmene
        self.versions = {}  # Verze imagu

    def _am_i_logged_in(self) -> bool:
        """
        Checks k8s login.
        """
        spc = self.cmd(
            ["kubectl", "auth", "can-i", "get", "deployment"],
            get_stdout=True,
        )
        return spc.returncode == 0

    def _confirm(self, message: str, default: str = "y") -> bool:
        res = input("{}{}: ".format(message, " [{}]".format(default)) if default else "")
        if res in SUCCESS_REPLY or (not res and default in SUCCESS_REPLY):
            return True
        return False

    def _input_text(self, message: str) -> str:
        text = ""
        while text == "":
            text = input(message)
        return text

    def _out(self, *args) -> None:
        if not self.args or not self.args.quiet:
            print(*args)

    def _create_conf_file(self, outfile: str, template: str, data: Dict[str, str] = None) -> None:
        with open(outfile, 'w') as fp:
            content = template.format(**data) if data else template
            fp.write(content)

    def init_env(self) -> None:
        """
        Initialize project for vindaloo.
        """
        os.chdir(self.args.dir)
        if self._check_current_dir():
            self.fail("Project already contains `k8s` directory.")

        maintainer_name = self._input_text("Your full name: ")
        maintainer_email = self._input_text("Your email: ")
        k8s_prefix = self._input_text("K8S namespace prefix (usualy name of team, for example. [avengers]-stable): ")
        k8s_prefix = k8s_prefix.rstrip('-')
        k8s_clusters = self._input_text("K8S cluster names (separated by comma): ")
        k8s_clusters = k8s_clusters.split(',')
        docker_registry = self._input_text("Docker registry hostname: ")
        image_name = self._input_text("Name of docker repository (for example: avengers/web): ")
        ident_label = image_name.split('/')[1]

        os.mkdir(CONFIG_DIR)

        # lets make global config
        self._create_conf_file(
            '{}.py'.format(ENVS_CONFIG_NAME),
            EXAMPLE_VINDALOO_CONF,
            dict(
                k8s_prefix=k8s_prefix,
                docker_registry=docker_registry,
                k8s_clusters=k8s_clusters,
            )
        )

        # lets create base.py, dev.py and versions.json
        self._create_conf_file(
            '{}/base.py'.format(CONFIG_DIR),
            EXAMPLE_BASE,
            dict(
                maintainer_name=maintainer_name,
                maintainer_email=maintainer_email,
                image_name=image_name,
                ident_label=ident_label,
            )
        )
        self._create_conf_file(
            '{}/dev.py'.format(CONFIG_DIR),
            EXAMPLE_DEV,
        )

        self._create_conf_file(
            '{}/versions.json'.format(CONFIG_DIR),
            json.dumps({image_name: "1.0.0"}, indent=2),
        )

        templates_dir = os.path.join(CONFIG_DIR, 'templates')
        os.mkdir(templates_dir)

        # basic templates (Dockerfile, deployment, service)
        self._create_conf_file(
            '{}/Dockerfile'.format(templates_dir),
            EXAMPLE_DOCKERFILE,
            dict(docker_registry=docker_registry),
        )
        self._create_conf_file(
            '{}/deployment.yaml'.format(templates_dir),
            EXAMPLE_DEPLOYMENT
        )
        self._create_conf_file(
            '{}/service.yaml'.format(templates_dir),
            EXAMPLE_SERVICE
        )

    def convert_manifest(self):
        import yaml
        with open(self.args.manifest, 'r') as fp:
            manifest_data = yaml.load(fp, Loader=yaml.Loader)
            res = get_obj_repr_from_dict(manifest_data)
            self._out(res)

    def k8s_select_env(self) -> None:
        """
        Switch to selected K8S context.
        """
        dep_env = self.args.environment
        if dep_env not in self.envs_config_module.ENVS:
            self.fail("Unknown environment '{}'.".format(dep_env))
        self._select_k8s_context(dep_env, self.args.cluster)

    def k8s_deploy(self) -> None:
        """
        Nasadi komponentu do K8S
        """
        dep_env = self.args.environment

        if dep_env not in self.envs_config_module.ENVS:
            self.fail("Unknown environment '{}'.".format(dep_env))

        self.config_module = self._import_config(dep_env)
        if not self.config_module:
            self.fail(f"Environment '{dep_env}' does not have configuration.")

        # prepneme se
        if not self.args.apply_output_dir:
            self._select_k8s_context(dep_env, self.args.cluster)

        # pro jednotlive typy souboru vygenerujeme yaml soubory a nasadime je
        for obj_type in K8S_OBJECT_TYPES:
            if obj_type not in self.config_module.K8S_OBJECTS:
                continue  # Pokud tenhle typ nema tak jedeme dal

            for yaml_conf in self.config_module.K8S_OBJECTS[obj_type]:
                if isinstance(yaml_conf, JsonSerializable):
                    temp_file = self._create_json_file_from_object(yaml_conf)
                    ident = yaml_conf.name
                else:
                    # pridame registry
                    yaml_conf['config']['registry'] = self.registry

                    temp_file = self.create_file(yaml_conf['template'], yaml_conf['config'], from_templates=True)
                    ident = yaml_conf['config'].get('ident_label', 'unnamed')

                if not temp_file:
                    self.fail("Error while creating deployment file.")

                assert self.kubectl_apply(
                    temp_file.name, name=ident, object_type=obj_type
                )

        if self.args.watch:
            failed_deployments = []
            for yaml_conf in self.config_module.K8S_OBJECTS.get('deployment', []):
                if isinstance(yaml_conf, JsonSerializable):
                    deployment_name = yaml_conf.name
                else:
                    deployment_name = yaml_conf.get('config', {}).get('ident_label', '')
                if deployment_name:
                    self._out('Waiting for rollout {} to finish'.format(deployment_name))
                    if not self._cmd_check(["kubectl", "rollout", "status", "deployment", deployment_name]):
                        failed_deployments.append(deployment_name)

            failed_jobs = []
            for yaml_conf in self.config_module.K8S_OBJECTS.get('job', []):
                if isinstance(yaml_conf, JsonSerializable):
                    job_name = yaml_conf.name

                if job_name:
                    self._out('Waiting for job {} to finish'.format(job_name))
                    succeeded, failed = None, None
                    while not succeeded and not failed:
                        time.sleep(60)  # one minute wait for not messing up kube
                        succeeded = self.cmd(["kubectl", "get", "job", job_name, "-o", "jsonpath={.status.succeeded}"], get_stdout=True).stdout
                        failed = self.cmd(["kubectl", "get", "job", job_name, "-o", "jsonpath={.status.failed}"], get_stdout=True).stdout
                        if succeeded:
                            self._out("Job {} ended successfully.".format(job_name))
                        if failed:
                            failed_jobs.append(job_name)
                            self._out("Job {} failed.".format(job_name))

            if failed_deployments:
                self.fail("Vindaloo stopped working due to failed deployments: {}".format(failed_deployments))
            if failed_jobs:
                self.fail("Vindaloo stopped working due to failed jobs: {}".format(failed_jobs))

    def kubectl_apply(self, filename: str, name: str = 'unnamed', object_type: str = 'k8s_object') -> bool:
        """
        Apply k8s JSON or save into output dir, when specified on command line.
        """
        if self.args.dryrun:
            self._out("CALL: kubectl apply -f {}".format(filename))
            return True
        elif self.args.apply_output_dir:
            os.makedirs(self.args.apply_output_dir, exist_ok=True)

            if self.args.priority_prefix:
                prefix_ = K8S_OBJECT_TYPES_YAML_PREFIX.get(object_type)
                if prefix_:
                    prefix_ += "_"
            else:
                prefix_ = ""

            dest_filename = os.path.join(
                self.args.apply_output_dir,
                "{}{}_{}.json".format(prefix_, name, object_type)
            )
            shutil.copy(filename, dest_filename)
            self._out("{} created.".format(dest_filename))
            return True
        else:
            res = self.cmd(["kubectl", "apply", "-f", filename])
            return res.returncode == 0

    def _import_envs_config(self) -> None:
        """
        Reads main configuration containing list of clusters and namespaces.
        """
        dir = os.path.abspath(os.getcwd())

        while dir != '/':
            module = os.path.join(dir, ENVS_CONFIG_NAME)
            path = '{}.py'.format(module)
            if os.path.isfile(path):
                self.envs_config_module = imp.load_source(module, path)
                break

            # try parent dir.
            dir = os.path.abspath(os.path.join(dir, '..'))

    def _load_versions(self):
        """
        Loads image versions from `versions.json`
        """
        if self.versions:
            return

        with open('{}/versions.json'.format(CONFIG_DIR)) as fp:
            content = fp.read()
            if GIT_HASH_PLACEHOLDER in content:
                res = self.cmd(
                    ['git', 'rev-parse', '--short=8', 'HEAD'],
                    run_always=True,
                    get_stdout=True,
                )
                commit_hash = res.stdout.decode('utf8').strip()
                content = chevron.render(content, {'git': commit_hash})

        self.versions = json.loads(content)

    def _import_config(self, env: str) -> Any:
        """
        Nacte konfiguraci pro zadane prostredi
        """
        # Make sure it's file, to prevent importing some module from python path with same name
        if not os.path.isfile("{}/{}.py".format(CONFIG_DIR, env)):
            return None

        self._load_versions()
        sys.modules['vindaloo'].app = self
        sys.path.insert(0, os.path.abspath(CONFIG_DIR))
        try:
            # If there is already, remove from modules and import again
            if env in sys.modules:
                del sys.modules[env]
            res_mod = import_module(env)
            return res_mod
        except ModuleNotFoundError as ex:
            if env not in str(ex):
                self.fail(f"Error importing env configuration: {ex}")
            return None
        finally:
            sys.path = sys.path[1:]

    def _check_current_dir(self) -> bool:
        """
        Check if current dir contains k8s subdir.
        """
        return os.path.isdir(CONFIG_DIR)

    def cmd(self, command: List[str],
            get_stdout: bool = False, run_always: bool = False) -> subprocess.CompletedProcess:
        """
        Runs command as subprocess.
        """
        if self.args.debug:
            self._out("CALL: ", ' '.join(command))
        if self.args.dryrun:
            self._out("CALL: ", ' '.join(command))
            if not run_always:
                return subprocess.run('true')  # zavolam 'true' abych mohl vratit vysledek

        kwargs = {}
        if get_stdout:
            kwargs['stdout'] = subprocess.PIPE
            kwargs['stderr'] = subprocess.PIPE

        return subprocess.run(command, **kwargs)

    def _cmd_check(self, command: List[str], get_stdout: bool = False) -> bool:
        """
        Runs command and returns if finished successfully.
        """
        return self.cmd(command, get_stdout).returncode == 0

    def fail(self, msg: str) -> None:
        """
        Exits with error message (-1)
        """
        self._out(msg)
        sys.exit(-1)

    def _image_name_with_tag(self, conf: Dict, tag: str = None, registry: str = None) -> str:
        """
        Returns whole image name including tag.
        """

        image_name = "{}:{}".format(
            conf['image_name'],
            tag or conf['version'],
        )
        pure_image_name = self._strip_image_name(image_name)

        return '{}/{}'.format(
            registry or self.registry,
            pure_image_name,
        )

    @property
    def registry(self) -> str:
        """
        Returns registry according to current environment.
        """
        if (
                hasattr(self.args, 'environment') and
                self.args.environment in self.envs_config_module.ENVS
        ):
            return self.envs_config_module.ENVS[self.args.environment]['docker_registry']
        return ''

    @property
    def args_image(self) -> List[str]:
        """
        List of images.
        """
        return [x for x in self.args.image if x]

    def build_images(self) -> None:
        """
        Starts build of images without caching.
        """

        for conf in self.config_module.DOCKER_FILES:
            image_name = conf['config']['image_name']
            pure_image_name = self._strip_image_name(image_name)

            if self.args_image:
                # jmeno bez hostu, napr. avengers/adminserver
                if pure_image_name not in self.args_image:
                    self._out('skipping image {}'.format(pure_image_name))
                    continue

            self._create_dockerfile(conf)
            if conf.get('pre_build_msg') and not self.args.noninteractive:
                if not self._confirm("{}\nContinue?".format(conf['pre_build_msg'])):
                    continue

            command_args = [
                "docker",
                "build",
                "-t",
                self._image_name_with_tag(conf['config'])
            ]
            if not self.args.cache:
                command_args.append("--no-cache")
            if self.args.latest:
                command_args.extend([
                    '-t',
                    '{}/{}:latest'.format(self.registry, pure_image_name),
                ])
            command_args.extend([
                "-f",
                "Dockerfile",
                conf.get('context_dir', '.'),
            ])
            res = self.cmd(command_args)
            assert res.returncode == 0

    def pull_images(self) -> None:
        """
        Pull image from registry.
        """
        known_images = self._get_local_images()

        for conf in self.config_module.DOCKER_FILES:

            image_name_with_tag = self._image_name_with_tag(conf['config'])
            image_name = conf['config']['image_name']
            # name without host, for example avengers/adminserver
            pure_image_name = self._strip_image_name(image_name)

            if self.args_image:
                if pure_image_name not in self.args_image:
                    self._out('skipping image {}'.format(pure_image_name))
                    continue

            if image_name_with_tag in known_images:
                self._out("skipping image {}, already pulled...".format(image_name_with_tag))
                continue

            res = self.cmd(["docker", "pull", image_name_with_tag])
            assert res.returncode == 0

    def push_images(self) -> None:
        """
        Starts push into registry.
        """

        known_images = self._get_local_images()

        for conf in self.config_module.DOCKER_FILES:

            image_name_with_tag = self._image_name_with_tag(conf['config'])
            image_name = conf['config']['image_name']
            # name without host, for example avengers/adminserver
            pure_image_name = self._strip_image_name(image_name)

            if self.args_image:
                if pure_image_name not in self.args_image:
                    self._out('skipping image {}'.format(pure_image_name))
                    continue

            if self.args.from_env:
                registry = self.envs_config_module.ENVS[self.args.from_env]['docker_registry']
                source_image = self._image_name_with_tag(conf['config'], registry=registry)

                if source_image not in known_images:
                    self._out("skipping image {}, it's not built yet...".format(source_image))
                    continue

                self._tag_image(source_image, image_name_with_tag)
                known_images = self._get_local_images()

            if image_name_with_tag not in known_images:
                self._out("skipping image {}, it's not built yet...".format(image_name_with_tag))
                continue

            if self.args.registry:
                # change registry in image_name
                source_image = image_name_with_tag
                image_name_with_tag = self._image_name_with_tag(conf['config'], registry=self.args.registry)
                # tag original image to contain new registry
                self._tag_image(source_image, image_name_with_tag)

            res = self.cmd(["docker", "push", image_name_with_tag])
            assert res.returncode == 0

            if self.args.latest:
                res = self.cmd(["docker", "push", self._image_name_with_tag(conf['config'], tag='latest')])
                assert res.returncode == 0

    def _tag_image(self, source_image: str, target_image: str) -> None:
        res = self.cmd(["docker", "tag", source_image, target_image])
        assert res.returncode == 0

    def _get_local_images(self) -> Set[str]:
        """
        Finds out built images in local docker, returns set of images in image:tag format.
        """
        res = self.cmd(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], get_stdout=True, run_always=True)
        images = set()
        for l in res.stdout.decode("utf-8").split("\n"):
            stripped = l.strip()
            images.add(stripped)
        return images

    def _strip_image_name(self, image_name: str) -> str:
        """
        Returns repository (aka name of image) without registry
        """
        if (
                hasattr(self.args, 'environment') and
                self.args.environment in self.envs_config_module.ENVS
        ):
            registry = self.envs_config_module.ENVS[self.args.environment]['docker_registry']
            if image_name.startswith(registry):
                return image_name[(image_name.find("/") + 1):]
        for env in self.envs_config_module.ENVS:
            registry = self.envs_config_module.ENVS[env]['docker_registry']
            if image_name.startswith(registry):
                return image_name[(image_name.find("/") + 1):]
        return image_name

    def _collect_local_versions(self, only_env: str = None) -> Dict:
        """
        Returns list of images defined for individual environments
        """
        local_versions = {}
        for env in self.envs_config_module.ENVS:
            if only_env and only_env != env:
                continue
            if self._import_config(env):
                images = {}
                for df_config in self.config_module.DOCKER_FILES:
                    conf = df_config['config']
                    images[self._strip_image_name(conf['image_name'])] = conf['version']
                local_versions[env] = images

        return local_versions

    def _collect_remote_versions(self, only_env: str = None) -> Dict:
        """
        List of images for individual K8S namespaces.
        """
        remote_versions = {}  # type: Dict[str, Any]
        for env in self.envs_config_module.ENVS:
            if only_env and only_env != env:
                continue

            if self._import_config(env):
                for cluster in self.envs_config_module.ENVS[env].get('k8s_clusters', []):
                    self._select_k8s_context(env, cluster)
                    for deployment in self.config_module.K8S_OBJECTS.get("deployment", []):
                        if isinstance(deployment, JsonSerializable):
                            module_name = deployment.name
                        else:
                            module_name = deployment['config']['ident_label']
                        remote_images = self.get_k8s_deployment_version(module_name)
                        if not remote_images:
                            continue
                        images = remote_versions.get(env, {}).get(cluster, {})
                        for remote_image in remote_images:
                            parts = remote_image.split(":")
                            version = parts[-1]
                            image = self._strip_image_name(":".join(parts[:-1]))
                            images[image] = version
                        remote_versions.setdefault(env, {})[cluster] = images

        return remote_versions

    def collect_versions(self) -> None:
        """
        Compares local and remote image lists.
        """
        local_ = self._collect_local_versions(self.args.environment)
        remote_ = self._collect_remote_versions(self.args.environment)
        summary = {}  # type: Dict[str, Any]
        for env in local_:
            for image in local_[env]:
                summary.setdefault(env, {}).setdefault(
                    image, {'local': None, 'remote': {}}
                )["local"] = local_[env][image]
        for env in remote_:
            for cluster in remote_[env]:
                for image in remote_[env][cluster]:
                    summary.setdefault(env, {}).setdefault(
                        image, {'local': None, 'remote': {}}
                    )["remote"][cluster] = remote_[env][cluster][image]

        if self.args.json:
            print(json.dumps(summary, indent=1))

        self._out("\nImage and version for defined environments")
        for env in summary:
            self._out("\n{}:".format(env))
            for image_ in summary[env]:
                vers = summary[env][image_]
                warning = ""
                for cluster in self.envs_config_module.ENVS[env]['k8s_clusters']:
                    if vers["local"] != vers["remote"].get(cluster):
                        warning = " [DIFFERS]"
                self._out("Image: {} in config: {}, on server: {} {}".format(
                    image_, vers["local"], vers["remote"], warning
                ))

    def get_k8s_deployment_version(self, module_name: str) -> List[str]:
        """
        List of deployed images for deployment.
        """
        res = self.cmd([
            "kubectl", "get", "deployment", module_name,
            "-o=jsonpath='{$.spec.template.spec.containers[*].image}'"
        ], get_stdout=True)
        if res.returncode == 0 and res.stdout:
            output = res.stdout.decode("utf-8").strip("'").split(" ")
            return output
        else:
            return []

    def _select_k8s_context(self, env: str, cluster: str) -> None:
        """
        Change K8S context
        """
        if (
                hasattr(self.envs_config_module, 'K8S_CLUSTER_ALIASES') and
                cluster in self.envs_config_module.K8S_CLUSTER_ALIASES
        ):
            cluster = self.envs_config_module.K8S_CLUSTER_ALIASES[cluster]

        if not cluster:
            cluster = self.envs_config_module.ENVS[env]['k8s_clusters'][0]

        context = '{}:{}'.format(self.envs_config_module.ENVS[env]['k8s_namespace'], cluster)

        if not self._cmd_check(["kubectl", "config", "use-context", context], self.args.quiet):
            if not self._confirm("K8s context is not set {}. Should I create it?".format(context)):
                self._out('Deploy action terminated')
                sys.exit(0)
            username = self._input_text("Insert username for cluster {}: ".format(cluster))
            assert self._cmd_check([
                "kubectl", "config", "set-context", context, "--cluster={}".format(
                    cluster
                ),
                "--namespace={}".format(
                    self.envs_config_module.ENVS[env]['k8s_namespace']
                ), "--user={}".format(username)])
            assert self._cmd_check(["kubectl", "config", "use-context", context], self.args.quiet)
            self._out("Environment changed to {} ({})".format(env, context))

    def create_file(
            self,
            template_file_name: str,
            conf: Dict,
            force_dest_file: str = None,
            from_templates: bool = False,
            no_edit=False
    ) -> BinaryIO:
        """
        Creates Dockerfile/yaml file using given template and config dict.
        """
        if from_templates:
            src_file = "{}/templates/{}".format(CONFIG_DIR, template_file_name)
        else:
            src_file = "{}/{}".format(CONFIG_DIR, template_file_name)

        with open(src_file, "r") as template_file:
            # render using given variables
            data = chevron.render(template_file, conf)

        if force_dest_file:
            temp_file = open(force_dest_file, "w+b")
        else:
            temp_file = tempfile.NamedTemporaryFile("w+b")

        temp_file.write(bytes(data, 'utf-8'))
        temp_file.seek(0)

        # Optionally offers edit
        if not self.args.noninteractive and not no_edit:
            if self._confirm("File {} was created. Do you want to modify it?".format(template_file_name), default="n"):
                self._open_in_editor(temp_file)

        return temp_file

    def _create_json_file_from_object(
            self,
            obj: JsonSerializable,
            force_dest_file: str = None,
            no_edit=False
    ) -> BinaryIO:
        """
        Creates JSON file using given object.
        """
        if force_dest_file:
            temp_file = open(force_dest_file, "wb")
        else:
            temp_file = tempfile.NamedTemporaryFile("wb")

        temp_file.write(bytes(
            json.dumps(obj.serialize(app=self), indent=4),
            'utf-8'
        ))
        temp_file.seek(0)

        # Optionally offers edit
        if not self.args.noninteractive and not no_edit:
            if self._confirm("File {}-{}.json was created. Do you want to modify it?".format(obj.name, obj.obj_type), default="n"):
                self._open_in_editor(temp_file)

        return temp_file

    @staticmethod
    def _open_in_editor(temp_file: Any) -> None:
        editor = os.getenv('EDITOR', 'vi')
        subprocess.call('{} {}'.format(editor, temp_file.name), shell=True)

    def _get_enriched_config_context(self, conf: Dict) -> Dict:
        """
        returns config with includes made from templates
        using same config.
        """
        new_context = {}  # type: Dict[str, Any]

        # If there are includes, then we pregenerate them and include in context
        if 'includes' in conf:
            for key, rel_path in conf['includes'].items():
                assert os.path.exists(rel_path)
                with open(rel_path, "r") as include_file:
                    data = chevron.render(include_file, conf['config'])
                    new_context.setdefault('includes', {})[key] = data

        # Append config
        new_context.update(conf['config'])

        return new_context

    def _create_dockerfile(self, conf: Dict) -> None:
        """
        Creates Dockerfile using given template and config dict.
        """

        # config with includes
        tmp_config = self._get_enriched_config_context(conf)

        self.create_file(conf['template'], tmp_config, force_dest_file="Dockerfile", from_templates=True)

    def _check_version(self):
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(CHECK_VERSION_URL, timeout=0.5, context=context) as f:
                data = json.loads(f.read())
                if data.get('version') != VERSION:
                    self._out('Newer version found: {}, current version: {}'.format(
                        data.get('version'),
                        VERSION,
                    ))
        except Exception:
            pass

    def output_completion(self):
        self._out(argcomplete.shellcode(
            ['vindaloo'],
            False,
            'bash',
        ))

    def edit_secret(self) -> None:
        self.k8s_select_env()
        res = self.cmd(["kubectl", "get", "secrets", "-o", "json"], get_stdout=True, run_always=True)
        json_data = json.loads(res.stdout.decode('utf-8'))
        secrets = self._parse_secrets(json_data)
        while self._select_secret(secrets):
            pass

    @staticmethod
    def _parse_secrets(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = data.get("items", [])
        return [
            dict(
                name=i["metadata"]["name"],
                label="{} ({})".format(i["metadata"]["name"], i["type"]),
                values={k: base64.decodebytes(bytes(v, 'utf-8')) for k, v in i["data"].items()}
            ) for i in items
        ]

    def _select_secret(self, secrets: List[Dict[str, Any]]) -> bool:

        self.changed_secrets = {}
        self._out("\nSecrets in namespace\n")

        if not secrets:
            self._out("No secrets found.")
            return False

        options = [(str(idx+1), i["name"]) for idx, i in enumerate(secrets)] + [("x", "exit")]
        for i in options:
            self._out("{}) {}".format(i[0], i[1]))
        self._out("")

        choice = self._select("Select secret: ", options)
        if choice == "x":
            return False

        key = dict(options)[choice]
        item = next(x for x in secrets if x["name"] == key)  # vzdycky musi byt jedna odpoved

        while self._select_item(item):
            pass

        return True

    def _select_item(self, item: Dict[str, Any]) -> bool:
        self._out("\nValues in secret:\n")

        if not item["values"]:
            self._out("No values found.")
            return False

        options = [(str(idx+1), i) for idx, i in enumerate(item["values"].keys())]

        if self.changed_secrets:
            options.append(("c", "Commit changes ({})".format(len(self.changed_secrets))))

        options.append(("x", "<= back"))

        for i in options:
            self._out("{}) {}".format(i[0], i[1]))

        self._out("")

        choice = self._select("Select item to edit: ", options)
        if choice == "x":
            return False

        if choice == "c":
            self._commit_secret_values(item)
            return False

        key = dict(options)[choice]
        self._out("\nSelected:", key)

        val = item["values"][key]

        new_val = self._edit_value(val)

        if val == new_val:
            self._out("\nValue remains unchanged.\n")
            return True

        self.changed_secrets[key] = new_val

        return True

    @staticmethod
    def _select(question: str, options: Sequence[Sequence[str]]) -> str:
        res = None
        while res not in [x[0] for x in options]:
            res = input(question)

        return res

    @staticmethod
    def _edit_value(val: bytes) -> bytes:
        file_, path_ = tempfile.mkstemp()
        try:
            os.write(file_, val)
            os.close(file_)

            editor = os.getenv('EDITOR', 'vi')

            if editor in ["vi", "vim"]:  # Prevent adding NL at the EOF
                editor = editor + " -b"

            subprocess.call('{} {}'.format(editor, path_), shell=True)

            after_edit = open(path_, "rb").read()
            return after_edit

        finally:
            os.unlink(path_)

    def _commit_secret_values(self, item: Dict[str, Any]) -> None:
        changed = [
            '\"{}\":\"{}\"'.format(
                key,
                base64.encodebytes(val).decode("utf-8").replace("\n", "")
            ) for key, val in self.changed_secrets.items()
        ]
        cmd = ["kubectl", "patch", "secret", item["name"], "-p", "{{\"data\":{{{}}}}}".format(",".join(changed))]
        res = self.cmd(cmd)
        assert res.returncode == 0

        print("Saved!")

        raise RefreshException()  # Have to load data again

    def do_command(self, command: str = None) -> None:
        command = command or self.args.command

        if command == "init":
            self.init_env()
        elif command == "convert-manifest":
            self.convert_manifest()
        elif command == "build":
            self.build_images()
        elif command == "pull":
            self.pull_images()
        elif command == "push":
            self.push_images()
        elif command == "version":
            self._out(VERSION)
        elif command == "versions":
            self.collect_versions()
        elif command == "deploy":
            self.k8s_deploy()
        elif command == "deploy-dir":
            self.k8s_deploy()
        elif command == "kubeenv":
            self.k8s_select_env()
        elif command == "build-push-deploy":
            self.build_images()
            self.push_images()
            self.k8s_deploy()
        elif command == "completion":
            self.output_completion()
        elif command == "edit-secret":
            try:
                self.edit_secret()
            except RefreshException:
                self.edit_secret()

    def _image_completer(self, **kwargs):
        if not self.config_module:
            self.config_module = self._import_config(NONE)

        if not self.config_module:
            return []

        images = []
        for conf in self.config_module.DOCKER_FILES:
            image_name = conf['config']['image_name']
            images.append(self._strip_image_name(image_name))
        return images

    def get_arg_parser(self) -> argparse.ArgumentParser:
        envs = getattr(self.envs_config_module, 'ENVS', {})
        environments = envs.keys() if self.envs_config_module else tuple()
        clusters = set()
        for env in envs.values():
            clusters.update(env.get('k8s_clusters', []))

        if hasattr(self.envs_config_module, 'K8S_CLUSTER_ALIASES'):
            clusters.update(self.envs_config_module.K8S_CLUSTER_ALIASES.keys())

        clusters_str = ",".join(clusters)

        parser = argparse.ArgumentParser(description=self.__class__.__doc__)
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--noninteractive', action='store_true', help='Does not ask questions')
        parser.add_argument('--quiet', action='store_true', help='Suppress output')
        parser.add_argument('--dryrun', action='store_true', help='Just pretends, no changes are actually done')

        subparsers = parser.add_subparsers(title='commands', dest='command')

        init_parser = subparsers.add_parser('init', help='prepares project for Vindaloo')
        init_parser.add_argument('dir', help='project directory')

        convert_parser = subparsers.add_parser('convert-manifest', help='convert yaml manifest into Vindaloo config')
        convert_parser.add_argument('manifest', help='manifest file')

        build_parser = subparsers.add_parser('build', help='builds Docker images (all of them)')
        build_parser.add_argument(
            'environment', help='environment for which we want to build image',
            choices=environments,
        )
        build_parser.add_argument(
            'image', help='image we want to build', nargs='?', action='append'
        ).completer = self._image_completer
        build_parser.add_argument('--latest', help='tag image as latest', action='store_true')
        build_parser.add_argument('--cache', help='use cache', action='store_true')

        pull_parser = subparsers.add_parser('pull', help='pull docker images (all of them)')
        pull_parser.add_argument(
            'environment', help='environment for which we want to pull',
            choices=environments,
        )
        pull_parser.add_argument(
            'image', help='image we want to pull', nargs='?', action='append'
        ).completer = self._image_completer

        push_parser = subparsers.add_parser('push', help='push docker image (all of them)')
        push_parser.add_argument(
            'environment', help='environment for which we want to push',
            choices=environments,
        )
        push_parser.add_argument(
            'image', help='image we want to push', nargs='?', action='append'
        ).completer = self._image_completer
        push_parser.add_argument('--latest', help='push also as latest', action='store_true')
        push_parser.add_argument('--registry', help='tag image and push into different registry')
        push_parser.add_argument('--from-env', help='source env for which was the image built')

        kubeenv_parser = subparsers.add_parser('kubeenv', help='switch current kubernetes context in ENV')
        kubeenv_parser.add_argument(
            'environment', help='environment we want to switch',
            choices=environments,
        )
        kubeenv_parser.add_argument(
            'cluster', help='name of cluster ({})'.format(clusters_str),
            choices=clusters,
            nargs='?'
        )

        subparsers.add_parser('version', help='print version of Vindaloo')

        versions_parser = subparsers.add_parser('versions', help='list all images and compares to the cluster')
        versions_parser.add_argument('--json', help='output as json', action='store_true')
        versions_parser.add_argument(
            'environment',
            help='env for which we want comparison',
            choices=environments,
            nargs='?'
        )

        deploy_parser = subparsers.add_parser('deploy', help='Deploy project to cluster')
        deploy_parser.add_argument(
            '--watch', help='Wait for rollout of new version',
            action='store_true'
        )
        deploy_parser.add_argument(
            'environment', help='environment for deployment',
            choices=environments
        )
        deploy_parser.add_argument(
            'cluster', help='cluster name ({})'.format(clusters_str),
            choices=clusters,
            nargs='?'
        )

        deploy_dir_parser = subparsers.add_parser('deploy-dir', help='prepare deployment files')
        deploy_dir_parser.add_argument(
            'environment', help='environment for deployment',
            choices=environments
        )
        deploy_dir_parser.add_argument(
            'cluster', help='cluster name ({})'.format(clusters_str),
            choices=clusters,
            nargs='?'
        )
        deploy_dir_parser.add_argument(
            '--apply-output-dir',
            help="Instead of apply save generated yaml files to specified directory",
            required=True
        )
        deploy_dir_parser.add_argument(
            '--priority-prefix', help='Add priority prefix to manifest names .. for example: 1_xxx_configmap.yaml',
            action='store_true',
            default=False
        )

        bpd_parser = subparsers.add_parser('build-push-deploy', help='makes all three steps in one')
        bpd_parser.add_argument(
            'environment', help='environment for deployment',
            choices=environments
        )
        bpd_parser.add_argument(
            'cluster', help='cluster name ({})'.format(clusters_str),
            choices=clusters,
            nargs='?'
        )
        bpd_parser.add_argument(
            'image', help='image we want to build/push', nargs='?', action='append'
        ).completer = self._image_completer
        bpd_parser.add_argument('--latest', help='push also as latest', action='store_true')
        bpd_parser.add_argument('--cache', help='use cache', action='store_true')
        bpd_parser.add_argument('--registry', help='tag image and push into different registry')
        bpd_parser.add_argument('--from-env', help='source env for which was the image built')
        bpd_parser.add_argument(
            '--watch', help='Wait for the new version to rollout',
            action='store_true'
        )
        bpd_parser.add_argument(
            '--apply-output-dir',
            help="Instead of apply save generated yaml files to specified directory",
            default=None
        )

        edit_parser = subparsers.add_parser('edit-secret', help='Edit secret in k8s namespace')
        edit_parser.add_argument(
            'environment',
            help='env for edit',
            choices=environments,
        )
        edit_parser.add_argument(
            'cluster', help='cluster name ({})'.format(clusters_str),
            choices=clusters,
            nargs='?'
        )

        subparsers.add_parser('completion', help='list commands for bash completion')

        argcomplete.autocomplete(parser)

        return parser

    def main(self) -> None:
        self._import_envs_config()

        if len(sys.argv) > 1 and sys.argv[1] not in DO_NOT_NEED_CONFIG_FILE:
            if not self.envs_config_module:
                self.fail("Config file {}.py not found in path".format(ENVS_CONFIG_NAME))
            elif not hasattr(self.envs_config_module, 'ENVS'):
                self.fail("Variable ENVS not found in {}".format(self.envs_config_module))

        parser = self.get_arg_parser()

        namespace, _ = parser.parse_known_args()
        self.args = NamespaceWithDefaultValue(namespace)

        if not self.args.command:
            parser.print_help()

        if getattr(self.args, 'json', None):
            self.args.quiet = True

        self.config_module = self._import_config(NONE)

        if self.args.command != 'completion':
            self._check_version()

        if self.args.command not in DO_NOT_NEED_CONFIG_FILE:
            if not self._check_current_dir() and self.args.command not in DO_NOT_NEED_K8S_DIR:
                self.fail("Directory does not contain k8s subdirectory or Dockerfile is missing. Are we in module directory?")

        if self.args.command in NEEDS_K8S_LOGIN and not self._am_i_logged_in():
            self.fail("You are not logged in Kubernetes")

        self.do_command()


def run():
    tool = Vindaloo()
    tool.main()


app = Vindaloo()
