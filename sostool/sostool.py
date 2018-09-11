#!/usr/bin/python3

import argparse
import json
import os
import shutil
import sys
import subprocess
import tempfile
from typing import List, Set

import pystache

from . import config
from .git_integration import Git

YES_OPTIONS = ["y", "Y", "a", "A"]

NONE = "base"
DEV = "dev"
TEST = "test"
STAGE = "stage"
PROD = "prod"

LOCAL_ENVS = [DEV, TEST, STAGE, PROD]

K8S_NAMESPACES = {
    DEV: "sos-dev",
    TEST: "sos-test",
    STAGE: "sos-stage",
    PROD: "sos-stable",
}

K8S_OBJECT_TYPES = [
    "podpreset", "deployment", "service", "ingres", "cronjob", "job"
]

DEFAULT_DEPLOY_DIR = "./deploy_files"
SUCCESS_REPLY = ("Y", "y", "a", "A")


class SosTool:
    """
    Nastroj pro usnadneni prace s dockerem a kubernetes
    """

    def __init__(self):
        self.config_module = None
        self.args = None

    def am_i_logged_in(self):
        spc = subprocess.call(
            ["kubectl", "auth", "can-i", "get", "deployment"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        return spc == 0

    def k8s_login(self):
        locality = self.args.cluster
        temp_file = tempfile.NamedTemporaryFile()
        temp_file.write(bytes(KUBE_LOGIN_SCRIPT, 'utf-8'))
        temp_file.flush()
        spc = subprocess.call(['bash', temp_file.name, locality])
        assert spc == 0

    def confirm(self, message, default="y"):
        res = input("{}{}: ".format(message, " [{}]".format(default)) if default else "")
        if res in SUCCESS_REPLY or (not res and default in SUCCESS_REPLY):
            return True
        return False

    def input_text(self, message):
        text = ""
        while text == "":
            text = input(message)
        return text

    def create_prod_deploy_dir(self):
        desired_dir = input("Do jakeho adresare chcete vystup? [{}]: ".format(DEFAULT_DEPLOY_DIR))
        if not desired_dir:
            desired_dir = DEFAULT_DEPLOY_DIR
        if os.path.isdir(desired_dir):
            if not self.confirm("Adresar jiz existuje, pouzijeme ho?"):
                return self.create_prod_deploy_dir()
        os.makedirs(desired_dir, exist_ok=True)
        return desired_dir

    def k8s_select_env(self):
        dep_env = self.args.environment
        if dep_env not in LOCAL_ENVS:
            self.fail("Musite zadat EXISTUJICI prostredi ktere chcete nasadit. {} nezname.".format(dep_env))
        self.select_k8s_env(dep_env)

    def k8s_deploy(self):
        dep_env = self.args.environment

        if dep_env not in LOCAL_ENVS:
            self.fail("Musite zadat EXISTUJICI prostredi ktere chcete nasadit. {} nezname.".format(dep_env))

        if not self.import_config(dep_env):
            self.fail("Musite zadat nakonfigurovane prostredi ktere chcete nasadit.")

        # prepneme se
        self.select_k8s_env(dep_env)

        # pokud je cilem produkce, tak jen budeme stosovat do adresare
        if dep_env == PROD:
            deploy_dir = self.create_prod_deploy_dir()

            # Vypiseme hlavicku to-do, uz proto aby se v pripade recyklace adresare nehromadily stare zaznamy :-)
            with open(os.path.join(deploy_dir, "todo.txt"), "w") as todo_file:
                todo_file.write("K8S Nasazeni:\n\n")

        else:
            deploy_dir = None

        # pro jednotlive typy souboru vygenerujeme yaml soubory a nasadime je

        yaml_files = []
        for obj_type in K8S_OBJECT_TYPES:
            if obj_type not in self.config_module.K8S_OBJECTS:
                continue  # Pokud tenhle typ nema tak jedeme dal
            for yaml_conf in self.config_module.K8S_OBJECTS[obj_type]:

                temp_config = self.get_enriched_config_context(yaml_conf)

                temp_file = self.create_file(yaml_conf['template'], yaml_conf['config'])

                if not temp_file:
                    self.fail("Chyba pri vytvareni deployment souboru")

                if dep_env == PROD:
                    temp_file_name = "sos-{}_{}".format(yaml_conf['config']['ident_label'], yaml_conf['template'])
                    # potrebujeme abspath, protozer pak hodne menime adresare
                    deploy_file = os.path.abspath(os.path.join(deploy_dir, temp_file_name))
                    shutil.copy(temp_file.name, deploy_file)
                    with open(os.path.join(deploy_dir, "todo.txt"), "a+") as todo_file:
                        todo_file.write(" ".join(["kubectl", "apply", "-f", temp_file_name]))
                        todo_file.write("\n")
                    yaml_files.append(deploy_file)
                else:
                    res = self.cmd(["kubectl", "apply", "-f", temp_file.name])
                    assert res.returncode == 0

        if deploy_dir:
            print("Deployment pripraven v adresari {}.".format(deploy_dir))
            if yaml_files and not self.args.dryrun:
                if self.confirm("Mam to rovnou poslat do gitlabu k nasazeni?"):
                    self.send_yaml_files_to_gitlab(yaml_files)
                    print("OK, je to v mastru.")

            if self.confirm("Mam vypsat noticky na deploy?"):
                with open(os.path.join(deploy_dir, "todo.txt"), "r") as todo_file:
                    print("")
                    print(todo_file.read())

    def import_config(self, env):
        # radsi checkneme ze mame soubor, abysme neimportovali nejaky jiny modul z path...
        if not os.path.isfile("k8s/{}.py".format(env)):
            return None

        versions = json.load(open('k8s/versions.json'))
        sys.modules['versions'] = versions
        sys.path.insert(0, "k8s")

        try:
            if sys.version_info[0] > 2:
                from importlib import import_module
            else:
                from importlib2 import import_module
            return import_module(env)
        except ModuleNotFoundError:
            return None
        finally:
            sys.path = sys.path[1:]

    def check_current_dir(self):
        return os.path.isdir("k8s")

    def cmd(self, command, get_stdout=False):
        if self.args.debug:
            print("CALL: ", ' '.join(command))
        if self.args.dryrun:
            print("CALL: ", ' '.join(command))
            return subprocess.run('true')  # zavolam 'true' abych mohl vratit vysledek

        kwargs = {}
        if get_stdout:
            kwargs['stdout'] = subprocess.PIPE
            kwargs['stderr'] = subprocess.PIPE

        return subprocess.run(command, **kwargs)

    def cmd_check(self, command, get_stdout=False):
        return self.cmd(command, get_stdout).returncode == 0

    def fail(self, msg):
        print(msg)
        sys.exit(-1)

    def image_name(self, conf):
        image_name = "{}:{}".format(
            conf['image_name'],
            conf['version'],
        )
        return image_name


    @property
    def args_image(self):
        """
        Vraci seznam imagu. Cisti argsy od None
        """
        return [x for x in self.args.image if x]

    def build_images(self):
        """Spusti build image bez cachovani"""

        for conf in self.config_module.DOCKER_FILES:
            if self.args_image:
                image_name = conf['config']['image_name']
                # jmeno bez hostu, napr. sos/adminserver
                pure_image_name = image_name[image_name.index('/') + 1:]
                if pure_image_name not in self.args_image:
                    print('preskakuju image {}'.format(pure_image_name))
                    continue

            self.create_dockerfile(conf)
            if conf.get('pre_build_msg') and not self.args.noninteractive:
                if not self.confirm("{}\nPokracujeme?".format(conf['pre_build_msg'])):
                    continue

            command_args = [
                "docker",
                "build",
                "--no-cache",
                "-t",
                self.image_name(conf['config']),
            ]
            if self.args.latest:
                command_args.extend([
                    '-t',
                    conf['config']['image_name'] + ':latest',
                ])
            command_args.extend([
                "-f",
                "Dockerfile",
                conf.get('context_dir', '.'),
            ])
            res = self.cmd(command_args)
            assert res.returncode == 0

    def pull_images(self):
        """Pullne image z registry"""
        known_images = self._get_local_images()

        for conf in self.config_module.DOCKER_FILES:

            image_name_with_tag = self.image_name(conf['config'])
            image_name = conf['config']['image_name']
            # jmeno bez hostu, napr. sos/adminserver
            pure_image_name = image_name[image_name.index('/') + 1:]

            if self.args_image:
                if pure_image_name not in self.args_image:
                    print('preskakuju image {}'.format(pure_image_name))
                    continue

            if image_name_with_tag in known_images:
                print("preskakuji image {}, je uz pullnuty...".format(image_name_with_tag))
                continue

            res = self.cmd(["docker", "pull", image_name_with_tag])
            assert res.returncode == 0

    def push_images(self):
        """Spusti push do registry"""

        known_images = self._get_local_images()

        for conf in self.config_module.DOCKER_FILES:

            image_name_with_tag = self.image_name(conf['config'])
            image_name = conf['config']['image_name']
            # jmeno bez hostu, napr. sos/adminserver
            pure_image_name = image_name[image_name.index('/') + 1:]

            if self.args_image:
                if pure_image_name not in self.args_image:
                    print('preskakuju image {}'.format(pure_image_name))
                    continue

            if image_name_with_tag not in known_images:
                print("preskakuji image {} neni ubuildeny...".format(image_name_with_tag))
                continue

            if self.args.registry:
                # zmenime v image_name registry
                conf['config']['image_name'] = '{}/{}'.format(self.args.registry, pure_image_name)
                source_image = image_name_with_tag
                image_name_with_tag = self.image_name(conf['config'])
                # tagneme puvodni image na jmeno s novou registry
                self.tag_image(source_image, image_name_with_tag)

            res = self.cmd(["docker", "push", image_name_with_tag])
            assert res.returncode == 0
            if self.args.latest:
                res = self.cmd(["docker", "push", conf['config']['image_name'] + ':latest'])
                assert res.returncode == 0

    def tag_image(self, source_image, target_image):
        """Otaguje image"""
        res = self.cmd(["docker", "tag", source_image, target_image])
        assert res.returncode == 0

    def _get_local_images(self):
        # type: () -> Set[str]
        """
        Zjisti jake image mame ubuildene v lokalnim dockeru, vraci set imagu v image:tag formatu.
        """
        res = self.cmd(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], get_stdout=True)
        images = set()
        for l in res.stdout.decode("utf-8").split("\n"):
            stripped = l.strip()
            images.add(stripped)
        return images

    def _strip_image_name(self, image_name):
        if image_name.startswith("doc.ker"):
            return image_name[(image_name.find("/") + 1):]
        else:
            return image_name

    def collect_local_versions(self, only_env=None):
        local_versions = {}
        for env in LOCAL_ENVS:
            if only_env and only_env != env:
                continue
            if self.import_config(env):
                images = {}
                for df_config in self.config_module.DOCKER_FILES:
                    conf = df_config['config']
                    images[self._strip_image_name(conf['image_name'])] = conf['version']
                local_versions[env] = images

        return local_versions

    def collect_remote_versions(self, only_env=None):
        remote_versions = {}
        for env in K8S_NAMESPACES:
            if only_env and only_env != env:
                continue

            if self.import_config(env):
                self.select_k8s_env(env)
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
                    remote_versions[env] = images

        return remote_versions

    def collect_versions(self):
        local_ = self.collect_local_versions(self.args.environment)
        remote_ = self.collect_remote_versions(self.args.environment)
        summary = {}
        for env in local_:
            for image in local_[env]:
                summary.setdefault(env, {}).setdefault(image, {'local': None, 'remote': None})["local"] = local_[env][image]
        for env in remote_:
            for image in remote_[env]:
                summary.setdefault(env, {}).setdefault(image, {'local': None, 'remote': None})["remote"] = remote_[env][image]

        print("\nPro definovana prostredi vzdy obraz a verze")
        for env in summary:
            print("\n{}:".format(env))
            for image_ in summary[env]:
                vers = summary[env][image_]
                warning = " [ROZDILNE]" if vers["local"] != vers["remote"] else ""
                print("Image: {} v konfigu: {}, na serveru: {} {}".format(image_, vers["local"], vers["remote"], warning))

    def get_k8s_deployment_version(self, module_name):
        res = self.cmd([
            "kubectl", "get", "deployment", module_name,
            "-o=jsonpath='{$.spec.template.spec.containers[*].image}'"
        ], get_stdout=True)
        if res.returncode == 0:
            output = res.stdout.decode("utf-8").strip("'").split(" ")
            return output
        else:
            return []

    def select_k8s_env(self, env):
        if not self.cmd_check(["kubectl", "config", "use-context", K8S_NAMESPACES[env]]):
            if not self.confirm("Neni nastaven kuberneti context pro {}. Mam ho vytvorit?".format(env)):
                print('Deploy byl ukoncen')
                sys.exit(0)
            username = self.input_text("Zadejte domenove jmeno: ")
            assert self.cmd_check([
                "kubectl", "config", "set-context", K8S_NAMESPACES[env], "--cluster=kube1.ko",
                "--namespace={}".format(K8S_NAMESPACES[env]), "--user={}".format(username)])
            assert self.cmd_check(["kubectl", "config", "use-context", K8S_NAMESPACES[env]])
            print("Prostredi zmeneneno na {}({})".format(env, K8S_NAMESPACES[env]))

    def send_yaml_files_to_gitlab(self, files: List[str], commit_message: str = "SOS nova verze") -> None:

        if not files or self.args.dryrun:
            return
        saved_dir = os.getcwd()  # Sem se pak budeme vracet
        try:
            git = Git(reuse_last_repo=False)
            git.init_workdir()
            for _ in git.get_repo(config.TT_GIT_REPO, print_it=False):
                pass
            for filename in files:
                print("{} -> {}".format(filename, os.path.join(git.get_copy_dir(), "sos-stable", os.path.basename(filename))))
                shutil.copy(filename, os.path.join(git.get_copy_dir(), "sos-stable", os.path.basename(filename)))
                git.add([os.path.join("sos-stable", os.path.basename(filename))])
            git.commit(commit_message)
            print("commitnuto")
            git.push_master()
            print("pushnuto")
        finally:
            os.chdir(saved_dir)  # vratime se do puvodniho adresare

    def create_file(self, template_file_name, conf, force_dest_file=None):
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
            temp_file = tempfile.NamedTemporaryFile()

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

    def get_enriched_config_context(self, conf):
        """
        returns config with includes made from templates
        using same config.
        """
        new_context = {}

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

    def create_dockerfile(self, conf):

        # config with includes
        tmp_config = self.get_enriched_config_context(conf)

        self.create_file(conf['template'], tmp_config, force_dest_file="Dockerfile")

    def do_command(self):
        command = self.args.command

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

    def main(self):

        NEEDS_K8S_LOGIN = ('versions', 'deploy', 'build-push-deploy')

        parser = argparse.ArgumentParser(description=self.__class__.__doc__)
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--noninteractive', action='store_true')
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
        kubeenv_parser.add_argument('environment', help='prostredi, kam chceme nasadit', choices=LOCAL_ENVS)

        versions_parser = subparsers.add_parser('versions', help='vypise verze vsech imagu a srovna s clusterem')
        versions_parser.add_argument('environment', help='env pro ktery chceme verze zobrazit', choices=LOCAL_ENVS, nargs='?')

        login_parser = subparsers.add_parser('kubelogin', help='prihlasi se do kubernetu')
        login_parser.add_argument('cluster', choices=('ko', 'ng'), default='ko', nargs='?')

        deploy_parser = subparsers.add_parser('deploy', help='nasadi zmeny do clusteru')
        deploy_parser.add_argument('environment', help='prostredi, kam chceme nasadit', choices=LOCAL_ENVS)

        bpd_parser = subparsers.add_parser('build-push-deploy', help='udela vsechny tri kroky')
        bpd_parser.add_argument('environment', help='prostredi, kam chceme nasadit', choices=LOCAL_ENVS)
        bpd_parser.add_argument('image', help='image, ktery chceme ubuildit/pushnout', nargs='?', action='append')
        bpd_parser.add_argument('--latest', help='pushnout image i jako latest', action='store_true')
        bpd_parser.add_argument('--registry', help='tagne image a pushne do jine registry')

        self.args, _ = parser.parse_known_args()

        self.config_module = self.import_config(NONE)

        if not self.check_current_dir():
            self.fail("Adresar neobsahuje slozku k8s nebo Dockerfile. Jsme uvnitr modulu?")

        if not self.am_i_logged_in() and self.args.command in NEEDS_K8S_LOGIN:
            self.fail("Nejste prihlaseni, zkuste 'sostool kubelogin'")

        self.do_command()


KUBE_LOGIN_SCRIPT = r"""#!/bin/bash
set -e -o pipefail

function fail {
    echo "Error: $1"
    exit 1
}

if [ $# -ne 1 ] || [[ "x$1" != "xko" && "x$1" != "xng" ]]; then
    echo "Usage $0 [ ko | ng ]"
    exit 0
fi

dc=$1

if [ "$dc" == "ko" ]; then
    ca_pem_url="https://gitlab.kancelar.seznam.cz/ultra/SCIF/k8s/documentation/uploads/1f7b7fbfe92edb9f8c76b223151b4aae/kube1.ko.pem"
else
    ca_pem_url="https://gitlab.kancelar.seznam.cz/ultra/SCIF/k8s/documentation/uploads/d51f1cd470c990025eeb313d4d0c97d6/kube1.ng.pem"
fi

kube_apiserver="https://tt-k8s1.${dc}.seznam.cz:6443/"
kube_cluster="kube1.${dc}"
kube_default_ns="sandbox"
ca_pem="${HOME}/.kube/ssl/${kube_cluster}.pem"

dex_uri="https://dex.${dc}.seznam.cz:30000/dex"
dex_client_id="kubernetes"
dex_client_secret="szn-supertajneheslo"
dex_redirect_uri="http://127.0.0.1:5555/callback"
dex_scope="openid+groups+profile+email"

# Fail if dependencies were not met
CURL=`which curl` || fail "can't find curl binary in your \${PATH}"

# Try to install kubectl
if [ -z "$(which kubectl)" ]; then
    read -p "kubectl is not installed, do you want to install it? (Press Y) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        exit 1
    fi

    # Test package managers and run them
    if [[ $(which brew) ]]; then
        brew install kubernetes-cli bash-completion
    elif [[ $(which gcloud) ]]; then
        gcloud components install kubectl
    elif [[ $(which snap) ]]; then
        sudo snap install kubectl --classic
    else
        fail "No known package managers were found, follow install instructions here:\nhttps://kubernetes.io/docs/tasks/tools/install-kubectl/"
    fi
fi

# Install certificate if not there
if [ ! -f ${ca_pem} ]; then
    curl -sS ${ca_pem_url} > ${ca_pem}
fi

# show LOGIN-NOTES.txt file
curl --max-time 1 -k https://gitlab.kancelar.seznam.cz/ultra/SCIF/k8s/documentatio n/raw/info-notice-to-gitlab-pages/LOGIN-NOTES.txt 2>/dev/null || true

dex_login_form_uri="${dex_uri}/auth?client_id=${dex_client_id}&client_secret=${dex_client_secret}&redirect_uri=${dex_redirect_uri}&scope=${dex_scope}&response_type=code"
dex_req_id=$(${CURL} -I  -s -L -X GET "${dex_login_form_uri}" | grep -i location | cut -d '=' -f 2 | tr -d '\r')

echo "req id: ${dex_req_id}"

echo -n "username: "
read username
echo -n "password: "
read -s password
echo
result=$(${CURL} --data-urlencode "login=${username}" --data-urlencode "password=${password}" -X POST -s "${dex_uri}/auth/ldap?req=${dex_req_id}")

if [ -n "${result}" ]; then
    echo "Login failed"
fi

dex_token_id=$(${CURL} -I -s -X GET "${dex_uri}/approval?req=${dex_req_id}" | grep -i location | tr '&' "\n" | grep 'code=' | cut -d '=' -f 2 )
response_json=$(${CURL} -s --data-urlencode -X POST -d "client_id=${dex_client_id}&client_secret=${dex_client_secret}&redirect_uri=${dex_redirect_uri}&scope=${dex_scope}&code=${dex_token_id}&grant_type=authorization_code" "${dex_uri}/token")
token=$(echo $response_json | sed s/.*\"id_token\":// | cut -d'"' -f2)
if [ $token = "error" ]; then
    fail $response_json
fi

kubectl config set-cluster ${kube_cluster} --server=${kube_apiserver} --certificate-authority=${ca_pem}
kubectl config set-context ${kube_cluster} --cluster=${kube_cluster} --namespace=${kube_default_ns} --user=${username}-${dc}
kubectl config use-context ${kube_cluster}
kubectl config set-credentials "${username}-${dc}" --token="${token}"
"""


def run():
    tool = SosTool()
    tool.main()
