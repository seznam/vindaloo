#!/usr/bin/python3

import os
import shutil
import sys
import subprocess
import tempfile
import pystache


YES_OPTIONS = ["y", "Y", "a", "A"]

DEBUG = False
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

    def __init__(self):
        self.config_module = None
        self.batch_mode = False

    def am_i_logged_in(self):
        spc = subprocess.call(
            ["kubectl", "auth", "can-i", "get", "deployment"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        return spc == 0

    def k8s_login(self, options):
        locality = options[0] if options else "ko"  # KO je default, asi by chtelo vymyslet lepe
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

    def create_prod_deploy_dir(self):
        desired_dir = input("Do jakeho adresare chcete vystup? [{}]: ".format(DEFAULT_DEPLOY_DIR))
        if not desired_dir:
            desired_dir = DEFAULT_DEPLOY_DIR
        if os.path.isdir(desired_dir):
            if not self.confirm("Adresar jiz existuje, pouzijeme ho?"):
                return self.create_prod_deploy_dir()
        os.makedirs(desired_dir, exist_ok=True)
        return desired_dir

    def k8s_deploy(self, options):
        if not options:
            self.fail("Musite zadat prostredi ktere chcete nasadit.")

        dep_env = options[0]

        if dep_env not in LOCAL_ENVS:
            self.fail("Musite zadat EXISTUJICI prostredi ktere chcete nasadit. {} nezname.".format(dep_env))

        if not self.import_config(dep_env):
            self.fail("Musite zadat nakonfigurovane prostredi ktere chcete nasadit.")

        # prepneme se
        self.select_k8s_env(dep_env)

        # pokud je cilem produkce, tak jen budeme stosovat do adresare
        if dep_env == PROD:
            deploy_dir = self.create_prod_deploy_dir()
        else:
            deploy_dir = None

        # pro jednotlive typy souboru vygenerujeme yaml soubory a nasadime je

        for obj_type in K8S_OBJECT_TYPES:
            if obj_type not in self.config_module.K8S_OBJECTS:
                continue  # Pokud tenhle typ nema tak jedeme dal
            for yaml_conf in self.config_module.K8S_OBJECTS[obj_type]:
                remote_version = self.get_remote_object_version(obj_type, yaml_conf['config']['ident_label'])
                if remote_version == yaml_conf['config']['file_version']:
                    print("Preskakuji {} nezmenil se".format(yaml_conf['template']))
                    continue
                elif not remote_version:
                    print("Na serveru zatim neni zadna verze.")

                temp_file = self.create_file(yaml_conf['template'], yaml_conf['config'])

                if not temp_file:
                    self.fail("Chyba pri vytvareni deployment souboru")

                if dep_env == PROD:
                    shutil.copy(temp_file.name, os.path.join(deploy_dir, yaml_conf['template']))
                    with open(os.path.join(deploy_dir, "todo.txt"), "a+") as todo_file:
                        todo_file.write(" ".join(["kubectl", "apply", "-f", yaml_conf['template']]))
                        todo_file.write("\n")
                else:
                    res = self.cmd(["kubectl", "apply", "-f", temp_file.name])
                    assert res.returncode == 0

        if deploy_dir:
            print("Deployment pripraven v adresari {}.".format(deploy_dir))

    def print_usage_and_exit(self):
        print(HELP)
        sys.exit(1)

    def import_config(self, env):
        # radsi checkneme ze mame soubor, abysme neimportovali nejaky jiny modul z path...
        if not os.path.isfile("k8s/{}.py".format(env)):
            return None

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
        if DEBUG:
            print("CALL", command)

        kwargs = {}
        if get_stdout:
            kwargs['stdout'] = subprocess.PIPE
            kwargs['stderr'] = subprocess.PIPE

        return subprocess.run(command, **kwargs)

    def fail(self, msg):
        print(msg)
        sys.exit(-1)

    def image_name(self, conf):
        image_name = "{}:{}".format(
            conf['image_name'],
            conf['version'],
        )
        return image_name

    def build_images(self):
        """Spusti build image bez cachovani"""
        for conf in self.config_module.DOCKER_FILES:
            self.create_dockerfile(conf)
            if conf.get('pre_build_msg'):
                if not self.confirm("{}\nPokracujeme?".format(conf['pre_build_msg'])):
                    continue
            res = self.cmd([
                "docker",
                "build",
                "--no-cache",
                "-t",
                self.image_name(conf['config']),
                "-f",
                "Dockerfile",
                conf['context_dir'],
            ])
            assert res.returncode == 0

    def push_images(self):
        """Spusti push do repa"""
        for conf in self.config_module.DOCKER_FILES:
            res = self.cmd(["docker", "push", self.image_name(conf['config'])])
            assert res.returncode == 0

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
        for env in K8S_NAMESPACES.keys():
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

    def collect_versions(self, options):
        local_ = self.collect_local_versions(options[0] if options else None)
        remote_ = self.collect_remote_versions(options[0] if options else None)
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
        assert self.cmd(["kubectl", "config", "use-context", K8S_NAMESPACES[env]]).returncode == 0

    def get_remote_object_version(self, object_type, module_name):
        res = self.cmd([
            "kubectl", "get", object_type, module_name,
            "-o=jsonpath='{$.metadata.annotations.file_version}'"
        ], get_stdout=True)
        if res.returncode != 0:
            output = res.stderr.decode("utf-8").strip("'")
            # Pokud jde o prvni deployment, tak remove version nemame.
            if "Error from server (NotFound)" in output:
                return None

        assert res.returncode == 0
        try:
            output = int(res.stdout.decode("utf-8").strip("'"))
        except Exception:
            output = None
        return output

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
        if not self.batch_mode:
            res = input("Vygenrovan {} chces si to jeste poeditovat? [n]:".format(template_file_name))
            if res in ("a", "y", "A", "Y"):
                editor = os.getenv('EDITOR', 'vi')
                spc = subprocess.call('{} {}'.format(editor, temp_file.name), shell=True)

                if spc == 0:
                    return temp_file

        return temp_file

    def create_dockerfile(self, conf):
        self.create_file(conf['template'], conf['config'], force_dest_file="Dockerfile")

    def do_command(self, command, options):

        if command == "build":
            self.build_images()
        elif command == "push":
            self.push_images()
        elif command == "versions":
            self.collect_versions(options)
        elif command == "kubelogin":
            self.k8s_login(options)
        elif command == "deploy":
            self.k8s_deploy(options)

    def main(self):

        self.config_module = self.import_config(NONE)

        if not self.check_current_dir():
            self.fail("Adresar neobsahuje slozku k8s nebo Dockerfile. Jsme uvnitr modulu?")

        if len(sys.argv) < 2:
            self.print_usage_and_exit()

        command = sys.argv[1]

        if not self.am_i_logged_in() and command != "kubelogin":
            self.fail("Nejste prihlaseni, zkuste 'sostool kubelogin'")

        self.do_command(command, sys.argv[2:])


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
curl --max-time 1 -k https://gitlab.kancelar.seznam.cz/ultra/SCIF/k8s/documentation/raw/info-notice-to-gitlab-pages/LOGIN-NOTES.txt 2>/dev/null || true

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

HELP = """
./sostool <command> [options, ...]

commands:

build - ubali Docker image (vsechny)

push - pushne docker image (vsechny)

versions - vypise verze vsech imagu a srovna s clusterem

kubelogin <ko|ng> - prihlasi se do kubernetu

deploy <env> - nasadi zmeny do clusteru

"""

if __name__ == "__main__":
    tool = SosTool()
    tool.main()
