#!/usr/bin/python3

import argparse
import imp
from importlib import import_module
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Set, BinaryIO

import pystache

from .login import KUBE_LOGIN_SCRIPT


NONE = "base"
K8S_OBJECT_TYPES = [
    "podpreset", "deployment", "service", "ingres", "cronjob", "job"
]
SUCCESS_REPLY = ("Y", "y", "a", "A")
ENVS_CONFIG_NAME = 'vindaloo_conf'
NEEDS_K8S_LOGIN = ('versions', 'deploy', 'build-push-deploy')


class Vindaloo:
    """
    Nastroj pro usnadneni prace s dockerem a kubernetes
    """

    def __init__(self):
        self.envs_config_module = None  # konfigurace prostredi (clustery, namespacy)
        self.config_module = None  # konfigurace aktualne vybraneho prostredi (Dockerfily, deploymenty, porty, ...)
        self.args = None

    def _am_i_logged_in(self) -> bool:
        """
        Zjisti zda-li jsme prihlaseni v kubectl
        """
        spc = self.cmd(
            ["kubectl", "auth", "can-i", "get", "deployment"],
            get_stdout=True,
        )
        return spc.returncode == 0

    def k8s_login(self) -> None:
        """
        Spusti bash skript na prihlaseni do k8s
        """
        locality = self.args.cluster
        temp_file = tempfile.NamedTemporaryFile()
        temp_file.write(bytes(KUBE_LOGIN_SCRIPT, 'utf-8'))
        temp_file.flush()
        spc = self.cmd(['bash', temp_file.name, locality])
        assert spc.returncode == 0

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

    def k8s_select_env(self) -> None:
        """
        Zmeni vybrany K8S kontext
        """
        dep_env = self.args.environment
        if dep_env not in self.envs_config_module.LOCAL_ENVS:
            self.fail("Musite zadat EXISTUJICI prostredi ktere chcete nasadit. {} nezname.".format(dep_env))
        self._select_k8s_context(dep_env, self.args.cluster)

    def k8s_deploy(self) -> None:
        """
        Nasadi komponentu do K8S
        """
        dep_env = self.args.environment

        if dep_env not in self.envs_config_module.LOCAL_ENVS:
            self.fail("Musite zadat EXISTUJICI prostredi ktere chcete nasadit. {} nezname.".format(dep_env))

        if not self._import_config(dep_env):
            self.fail("Musite zadat nakonfigurovane prostredi ktere chcete nasadit.")

        # prepneme se
        self._select_k8s_context(dep_env, self.args.cluster)

        # pro jednotlive typy souboru vygenerujeme yaml soubory a nasadime je
        for obj_type in K8S_OBJECT_TYPES:
            if obj_type not in self.config_module.K8S_OBJECTS:
                continue  # Pokud tenhle typ nema tak jedeme dal
            for yaml_conf in self.config_module.K8S_OBJECTS[obj_type]:
                # pridame registry
                yaml_conf['config']['registry'] = self.registry

                temp_file = self._create_file(yaml_conf['template'], yaml_conf['config'])

                if not temp_file:
                    self.fail("Chyba pri vytvareni deployment souboru")

                res = self.cmd(["kubectl", "apply", "-f", temp_file.name])
                assert res.returncode == 0

    def _import_envs_config(self) -> None:
        """
        Nacte hlavni konfiguraci, ktera obsahuje seznam klusteru a namespacu
        """
        dir = os.path.abspath(os.path.curdir)

        while dir != '/':
            module = os.path.join(dir, ENVS_CONFIG_NAME)
            path = '{}.py'.format(module)

            if os.path.isfile(path):
                self.envs_config_module = imp.load_source(module, path)
                break

            # zkusime o slozku vyse
            dir = os.path.abspath(os.path.join(dir, '..'))
        else:
            self.fail("Konfiguracni soubor {}.py nenalezen nikde v ceste".format(ENVS_CONFIG_NAME))

    def _import_config(self, env: str) -> Any:
        """
        Nacte konfiguraci pro zadane prostredi
        """
        # radsi checkneme ze mame soubor, abysme neimportovali nejaky jiny modul z path...
        if not os.path.isfile("k8s/{}.py".format(env)):
            return None

        versions = json.load(open('k8s/versions.json'))
        sys.modules['versions'] = versions
        sys.path.insert(0, "k8s")

        try:
            return import_module(env)
        except ModuleNotFoundError:
            return None
        finally:
            sys.path = sys.path[1:]

    def _check_current_dir(self) -> bool:
        """
        Zkontroluje jestli aktualni adresar obsahuje slozku `k8s`
        """
        return os.path.isdir("k8s")

    def cmd(self, command: List[str],
            get_stdout: bool = False, run_always: bool = False) -> subprocess.CompletedProcess:
        """
        Provede zadany prikaz jako podproces
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

    def _cmd_check(self, command: List[str], get_stdout: bool = False) -> subprocess.CompletedProcess:
        """
        Provede prikaz a vrati zda skoncil bez chyby
        """
        return self.cmd(command, get_stdout).returncode == 0

    def fail(self, msg: str) -> None:
        """
        Ukonci beh se zadanou zpravou a chybovym stavem (-1)
        """
        self._out(msg)
        sys.exit(-1)

    def _image_name_with_tag(self, conf: Dict, tag: str = None, registry: str = None) -> str:
        """
        Vrati cely nazev image vcetne tagu
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
        Vrati registry podle aktualniho prostredi
        """
        if (
                hasattr(self.args, 'environment') and
                self.args.environment in self.envs_config_module.ENVS_WITH_PROD_REGISTRY
        ):
            return 'doc.ker'
        return 'doc.ker.dev.dszn.cz'

    @property
    def args_image(self) -> List[str]:
        """
        Vraci seznam imagu. Cisti argsy od None
        """
        return [x for x in self.args.image if x]

    def build_images(self) -> None:
        """
        Spusti build imagu bez cachovani
        """

        for conf in self.config_module.DOCKER_FILES:
            image_name = conf['config']['image_name']
            pure_image_name = self._strip_image_name(image_name)

            if self.args_image:
                # jmeno bez hostu, napr. sos/adminserver
                if pure_image_name not in self.args_image:
                    self._out('preskakuju image {}'.format(pure_image_name))
                    continue

            self._create_dockerfile(conf)
            if conf.get('pre_build_msg') and not self.args.noninteractive:
                if not self._confirm("{}\nPokracujeme?".format(conf['pre_build_msg'])):
                    continue

            command_args = [
                "docker",
                "build",
                "--no-cache",
                "-t",
                self._image_name_with_tag(conf['config']),
            ]
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
        Pullne image z registry
        """
        known_images = self._get_local_images()

        for conf in self.config_module.DOCKER_FILES:

            image_name_with_tag = self._image_name_with_tag(conf['config'])
            image_name = conf['config']['image_name']
            # jmeno bez hostu, napr. sos/adminserver
            pure_image_name = self._strip_image_name(image_name)

            if self.args_image:
                if pure_image_name not in self.args_image:
                    self._out('preskakuju image {}'.format(pure_image_name))
                    continue

            if image_name_with_tag in known_images:
                self._out("preskakuji image {}, je uz pullnuty...".format(image_name_with_tag))
                continue

            res = self.cmd(["docker", "pull", image_name_with_tag])
            assert res.returncode == 0

    def push_images(self) -> None:
        """
        Spusti push do registry
        """

        known_images = self._get_local_images()

        for conf in self.config_module.DOCKER_FILES:

            image_name_with_tag = self._image_name_with_tag(conf['config'])
            image_name = conf['config']['image_name']
            # jmeno bez hostu, napr. sos/adminserver
            pure_image_name = self._strip_image_name(image_name)

            if self.args_image:
                if pure_image_name not in self.args_image:
                    self._out('preskakuju image {}'.format(pure_image_name))
                    continue

            if image_name_with_tag not in known_images:
                self._out("preskakuji image {} neni ubuildeny...".format(image_name_with_tag))
                continue

            if self.args.registry:
                # zmenime v image_name registry
                source_image = image_name_with_tag
                image_name_with_tag = self._image_name_with_tag(conf['config'], registry=self.args.registry)
                # tagneme puvodni image na jmeno s novou registry
                self._tag_image(source_image, image_name_with_tag)

            res = self.cmd(["docker", "push", image_name_with_tag])
            assert res.returncode == 0

            if self.args.latest:
                res = self.cmd(["docker", "push", self._image_name_with_tag(conf['config'], tag='latest')])
                assert res.returncode == 0

    def _tag_image(self, source_image: str, target_image: str) -> None:
        """
        Otaguje image
        """
        res = self.cmd(["docker", "tag", source_image, target_image])
        assert res.returncode == 0

    def _get_local_images(self) -> Set[str]:
        """
        Zjisti jake image mame ubuildene v lokalnim dockeru, vraci set imagu v image:tag formatu.
        """
        res = self.cmd(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], get_stdout=True, run_always=True)
        images = set()
        for l in res.stdout.decode("utf-8").split("\n"):
            stripped = l.strip()
            images.add(stripped)
        return images

    def _strip_image_name(self, image_name: str) -> str:
        """
        Vrati repository (aka nazev image) bez registry
        """
        if image_name.startswith("doc.ker"):
            return image_name[(image_name.find("/") + 1):]
        else:
            return image_name

    def _collect_local_versions(self, only_env: str = None) -> Dict:
        """
        Vrati seznam imagu definovanych pro jednotliva prostredi
        """
        local_versions = {}
        for env in self.envs_config_module.LOCAL_ENVS:
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
        Vrati seznam imagu nasazenych v jednotlivych K8S namespacech
        """
        remote_versions = {}  # type: Dict[str, Any]
        for env in self.envs_config_module.K8S_NAMESPACES:
            if only_env and only_env != env:
                continue

            if self._import_config(env):
                for cluster in self.envs_config_module.K8S_CLUSTERS:
                    self._select_k8s_context(env, cluster)
                    for deployment in self.config_module.K8S_OBJECTS.get("deployment", []):
                        module_name = deployment['config']['ident_label']
                        remote_images = self.get_k8s_deployment_version(module_name)
                        if not remote_images:
                            continue
                        images = {}
                        for remote_image in remote_images:
                            parts = remote_image.split(":")
                            version = parts[-1]
                            image = self._strip_image_name(":".join(parts[:-1]))
                            images[image] = version
                        remote_versions.setdefault(env, {})[cluster] = images

        return remote_versions

    def collect_versions(self) -> None:
        """
        Porovna lokalni a nasazene verze imagu
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

        self._out("\nPro definovana prostredi vzdy obraz a verze")
        for env in summary:
            self._out("\n{}:".format(env))
            for image_ in summary[env]:
                vers = summary[env][image_]
                warning = ""
                for cluster in self.envs_config_module.K8S_CLUSTERS:
                    if vers["local"] != vers["remote"].get(cluster):
                        warning = " [ROZDILNE]"
                self._out("Image: {} v konfigu: {}, na serveru: {} {}".format(
                    image_, vers["local"], vers["remote"], warning
                ))

    def get_k8s_deployment_version(self, module_name: str) -> List[str]:
        """
        Ziska z kubernetu seznam nasazenych imagu pro jeden deployment
        """
        res = self.cmd([
            "kubectl", "get", "deployment", module_name,
            "-o=jsonpath='{$.spec.template.spec.containers[*].image}'"
        ], get_stdout=True)
        if res.returncode == 0:
            output = res.stdout.decode("utf-8").strip("'").split(" ")
            return output
        else:
            return []

    def _select_k8s_context(self, env: str, cluster: str) -> None:
        """
        Prepne K8S kontext
        """
        context = '{}-{}'.format(self.envs_config_module.K8S_NAMESPACES[env], cluster)

        if not self._cmd_check(["kubectl", "config", "use-context", context]):
            if not self._confirm("Neni nastaven kuberneti context {}. Mam ho vytvorit?".format(context)):
                self._out('Deploy byl ukoncen')
                sys.exit(0)
            username = self._input_text("Zadejte domenove jmeno: ")
            assert self._cmd_check([
                "kubectl", "config", "set-context", context, "--cluster={}".format(
                    self.envs_config_module.K8S_CLUSTERS[cluster]
                ),
                "--namespace={}".format(
                    self.envs_config_module.K8S_NAMESPACES[env]
                ), "--user={}-{}".format(username, cluster)])
            assert self._cmd_check(["kubectl", "config", "use-context", context])
            self._out("Prostredi zmeneneno na {} ({})".format(env, context))

    def _create_file(self, template_file_name: str, conf: Dict, force_dest_file: str = None) -> BinaryIO:
        """
        Vytvori Dockerfile/yaml soubor ze zadane sablony a slovniku konfigurace
        """
        data = ""
        with open("k8s/templates/{}".format(template_file_name), "r") as template_file:
            renderer = pystache.Renderer()
            # Naparsujeme sablonu
            template = pystache.parse(template_file.read())
            # vezmeme si z konfigurace prislusnou promennou a vyrenderujeme
            data = renderer.render(template, conf)

        if force_dest_file:
            temp_file = open(force_dest_file, "wb")
        else:
            temp_file = tempfile.NamedTemporaryFile("wb")

        temp_file.write(bytes(data, 'utf-8'))
        temp_file.seek(0)

        # Volitelne nabidneme k editaci
        if not self.args.noninteractive:
            res = input("Vygenerovan {} chces si to jeste poeditovat? [n]:".format(template_file_name))
            if res in ("a", "y", "A", "Y"):
                editor = os.getenv('EDITOR', 'vi')
                spc = subprocess.call('{} {}'.format(editor, temp_file.name), shell=True)

                if spc == 0:
                    return temp_file

        return temp_file

    def _get_enriched_config_context(self, conf: Dict) -> Dict:
        """
        returns config with includes made from templates
        using same config.
        """
        new_context = {}  # type: Dict[str, Any]

        # Pokud jsou includy, tak je predgenerujeme a pridame do kontextu
        if 'includes' in conf:
            for key, rel_path in conf['includes'].items():
                assert os.path.exists(rel_path)
                with open(rel_path, "r") as include_file:
                    renderer = pystache.Renderer()
                    # Naparsujeme sablonu
                    template = pystache.parse(include_file.read())
                    # vezmeme si z konfigurace context pro Dockerfile a vyrenderuje
                    data = renderer.render(template, conf['config'])
                    new_context.setdefault('includes', {})[key] = data

        # Pripiseme tam konfiguraci
        new_context.update(conf['config'])

        return new_context

    def _create_dockerfile(self, conf: Dict) -> None:
        """
        Vytvori Dockerfile z sablony a predaneho slovniku konfigurace
        """

        # config with includes
        tmp_config = self._get_enriched_config_context(conf)

        self._create_file(conf['template'], tmp_config, force_dest_file="Dockerfile")

    def do_command(self, command: str = None) -> None:
        command = command or self.args.command

        if command == "build":
            self.build_images()
        elif command == "pull":
            self.pull_images()
        elif command == "push":
            self.push_images()
        elif command == "versions":
            self.collect_versions()
        elif command == "kubelogin":
            self.k8s_login()
        elif command == "deploy":
            self.k8s_deploy()
        elif command == "kubeenv":
            self.k8s_select_env()
        elif command == "build-push-deploy":
            self.build_images()
            self.push_images()
            self.k8s_deploy()

    def main(self) -> None:
        self._import_envs_config()

        parser = argparse.ArgumentParser(description=self.__class__.__doc__)
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--noninteractive', action='store_true', help='Na nic se nepta')
        parser.add_argument('--quiet', action='store_true', help='Potlaci vystup')
        parser.add_argument('--dryrun', action='store_true', help='Jen predstira, nedela zadne nevratne zmeny')

        subparsers = parser.add_subparsers(title='commands', dest='command')

        build_parser = subparsers.add_parser('build', help='ubali Docker image (vsechny)')
        build_parser.add_argument('image', help='image, ktery chceme ubildit', nargs='?', action='append')
        build_parser.add_argument('--latest', help='tagnout image i jako latest', action='store_true')

        pull_parser = subparsers.add_parser('pull', help='pullne docker image (vsechny)')
        pull_parser.add_argument('image', help='image, ktery chceme pullnout', nargs='?', action='append')

        push_parser = subparsers.add_parser('push', help='pushne docker image (vsechny)')
        push_parser.add_argument('image', help='image, ktery chceme pushnout', nargs='?', action='append')
        push_parser.add_argument('--latest', help='pushnout image i jako latest', action='store_true')
        push_parser.add_argument('--registry', help='tagne image a pushne do jine registry')

        kubeenv_parser = subparsers.add_parser('kubeenv', help='switchne aktualni kubernetes context v ENV')
        kubeenv_parser.add_argument(
            'environment', help='prostredi, kam chceme switchnout', choices=self.envs_config_module.LOCAL_ENVS
        )
        kubeenv_parser.add_argument(
            'cluster', help='nazev clusteru (ko/ng)', choices=self.envs_config_module.K8S_CLUSTERS,
            default='ko', nargs='?'
        )

        versions_parser = subparsers.add_parser('versions', help='vypise verze vsech imagu a srovna s clusterem')
        versions_parser.add_argument(
            'environment',
            help='env pro ktery chceme verze zobrazit',
            choices=self.envs_config_module.LOCAL_ENVS, nargs='?'
        )

        login_parser = subparsers.add_parser('kubelogin', help='prihlasi se do kubernetu')
        login_parser.add_argument(
            'cluster',
            help='nazev clusteru (ko/ng)',
            choices=self.envs_config_module.K8S_CLUSTERS, default='ko', nargs='?'
        )

        deploy_parser = subparsers.add_parser('deploy', help='nasadi zmeny do clusteru')
        deploy_parser.add_argument(
            'environment', help='prostredi, kam chceme nasadit', choices=self.envs_config_module.LOCAL_ENVS
        )
        deploy_parser.add_argument(
            'cluster', help='nazev clusteru (ko/ng)',
            choices=self.envs_config_module.K8S_CLUSTERS, default='ko', nargs='?'
        )

        bpd_parser = subparsers.add_parser('build-push-deploy', help='udela vsechny tri kroky')
        bpd_parser.add_argument(
            'environment', help='prostredi, kam chceme nasadit', choices=self.envs_config_module.LOCAL_ENVS
        )
        bpd_parser.add_argument(
            'cluster', help='nazev clusteru (ko/ng)',
            choices=self.envs_config_module.K8S_CLUSTERS, default='ko', nargs='?'
        )
        bpd_parser.add_argument('image', help='image, ktery chceme ubuildit/pushnout', nargs='?', action='append')
        bpd_parser.add_argument('--latest', help='pushnout image i jako latest', action='store_true')
        bpd_parser.add_argument('--registry', help='tagne image a pushne do jine registry')

        self.args, _ = parser.parse_known_args()

        self.config_module = self._import_config(NONE)

        if not self._check_current_dir():
            self.fail("Adresar neobsahuje slozku k8s nebo Dockerfile. Jsme uvnitr modulu?")

        if self.args.command in NEEDS_K8S_LOGIN and not self._am_i_logged_in():
            self.fail("Nejste prihlaseni, zkuste 'sostool kubelogin'")

        self.do_command()


def run():
    tool = Vindaloo()
    tool.main()
