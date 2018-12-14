#!/bin/bash
set -e -o pipefail

fail() {
    echo "ERROR: $@"
    exit 1
}

warning() {
    echo "WARNING: $@"
}

# Detect if this is macOS
macos=$(echo $OSTYPE | sed -e '1s/^darwin.*$/yes/')

# Default namespace for newcomers, empty (do not change namespace by default) for others
namespace=$(test -f ~/.kube/config || echo sandbox)

version=2.1.3

testing=0

# Non macOS help
_help() {
    echo "
Login to scif.cz k8s cluster

Usage:
  $0 [-u|--user USER] [-p|--pass PASS] [-n|--namespace NAMESPACE] [-h|--help | -v|--version]

Options:
  -u --user USER             User to be used, if not passed, you will be prompted interactivelly.
  -p --pass PASS             Password to be used, if not passed, you will be prompted interactivelly.
  -n --namespace NAMESPACE   Namespace to use after login
  -t --test                  Login to testing clusters
  -h --help                  Prints this help.
  -v --version               Print version.
"
}


# macOS help - macOS by default does not support long options
_help_mac() {
    echo "
Login to scif.cz k8s cluster

Usage:
  $0 [-u USER] [-p PASS] [-n NAMESPACE] [-h | -v]

Options:
  -u USER        User to be used, if not passed, you will be prompted interactivelly.
  -p PASS        Password to be used, if not passed, you will be prompted interactivelly.
  -n NAMESPACE   Namespace to use after login
  -t             Login to testing clusters
  -h             Prints this help.
  -v             Print version.
"
}

if [ $macos = "yes" ]; then
    # do not use $@, see man getopt
    pargs=`getopt hvu:p:n:t $*`
    set -- $pargs
else
    pargs=$(getopt -o "h,v,u:,p:,n:,t" -l "help,version,user:,pass:,namespace:test" -n "$0" -- "$@")
    eval set -- "$pargs"
fi

while [ $# -gt 0 ]
do
  case "$1" in
    -h|--help)
        if [ $macos = "yes" ]; then
            _help_mac
        else
            _help
        fi
        exit
        ;;
    -v|--version)
        echo "$version"
        exit
        ;;
    -u|--user)
        username="$2"; shift
        shift
        ;;
    -p|--pass)
        password="$2"; shift
        shift
        ;;
    -n|--namespace)
        namespace="$2"; shift
        shift
        ;;
    -t|--test)
        testing=1
        shift
        ;;
    --)
        shift
        break
        ;;
  esac
done

# parse rest of arguments for deprecated options
if [[ "$1" =~ ^(ko|ko1|ko2|ng|ng1)$ ]]; then
    echo "!!!"
    echo "context switch is no longer supported"
    echo "use kubectx https://github.com/ahmetb/kubectx"
    echo "!!!"
    echo
fi

# Fail if dependencies were not met
CURL=$(which curl) || fail "can't find curl binary in your \${PATH}"

# Try to install kubectl
if [ -z "$(which kubectl)" ]; then
    read -p "kubectl is not installed, do you want to install it? (Press Y) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
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

# show LOGIN-NOTES.txt file
curl --max-time 1 https://gitlab.kancelar.seznam.cz/ultra/SCIF/k8s/documentation/raw/master/LOGIN_NOTES.txt 2>/dev/null || warning "Failed to download login notes"

if [ -z ${username+x} ]; then
    echo -n "username: "
    read username
else
    echo "Username: $username"
fi


if [ -z ${password+x} ]; then
    echo -n "password: "
    read -s password
fi

echo

k8s_login() {
    dc=$1
    kubeconfig_username=$2

    echo
    echo "Logging to ${dc} clusters"

    dex_uri_ko="https://dex.ko.seznam.cz:30000/dex"
    dex_uri_ng="https://dex.ng.seznam.cz:30000/dex"
    dex_uri_ko_test="https://dex-test.ko.seznam.cz:30000/dex"

    dex_var_name="dex_uri_${dc}"
    dex_uri=${!dex_var_name}

    dex_client_id="kubernetes"
    dex_client_secret="szn-supertajneheslo"
    dex_redirect_uri="http://127.0.0.1:5555/callback"
    dex_scope="openid+groups+profile+email"

    dex_login_form_uri="${dex_uri}/auth?client_id=${dex_client_id}&client_secret=${dex_client_secret}&redirect_uri=${dex_redirect_uri}&scope=${dex_scope}&response_type=code"
    dex_req_id=$(${CURL} -I  -s -L -X GET "${dex_login_form_uri}" | grep -i location | cut -d '=' -f 2 | tr -d '\r')

    echo "req id: ${dex_req_id}"

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

    kubectl config set-credentials "${kubeconfig_username}" --token="${token}"
}

config_kubectl() {
    cluster_id=$1
    kube_ns=$2
    kubeconfig_username=$3
    kube_apiserver="$4"

    kube_cluster="kube${cluster_id}"
    echo
    echo "Configuring kubectl for accessing ${kube_cluster} cluster"

    ca_pem_url="https://gitlab.kancelar.seznam.cz/ultra/SCIF/k8s/documentation/raw/master/certs/tt-k8s${cluster_id}.pem"

    ca_pem="${HOME}/.kube/ssl/${kube_cluster}.pem"

    # Install certificate if not there
    if [ ! -f "${ca_pem}" ]; then
        mkdir -p "$(dirname "${ca_pem}")"
        curl --fail -sS ${ca_pem_url} --output "${ca_pem}" || fail "Unable to download ${kube_cluster} cluster API CA certificate"
    fi

    kubectl config set-cluster ${kube_cluster} --server=${kube_apiserver} --certificate-authority=${ca_pem}

    if [ -z $kube_ns ]; then
        kubectl config set-context ${kube_cluster} --cluster=${kube_cluster} --user=${kubeconfig_username}
    else
        kubectl config set-context ${kube_cluster} --cluster=${kube_cluster} --namespace=${kube_ns} --user=${kubeconfig_username}
    fi
}

kubeconfig_username_ko="${username}-ko"
kubeconfig_username_ng="${username}-ng"
kubeconfig_username_ko_test="${username}-ko-test"

kube_apiserver_ko1="https://tt-k8s1.ko.seznam.cz:6443"
kube_apiserver_ng1="https://tt-k8s1.ng.seznam.cz:6443"
kube_apiserver_ko2="https://tt-k8s2.ko.seznam.cz:6443"
kube_apiserver_ng2="https://tt-k8s2.ng.seznam.cz:6443"
kube_apiserver_ko_test="https://tt-k8st1.ko.seznam.cz:6443"

k8s_login ko "$kubeconfig_username_ko"
k8s_login ng "$kubeconfig_username_ng"

config_kubectl "1.ko" "$namespace" "$kubeconfig_username_ko" "$kube_apiserver_ko1"
config_kubectl "1.ng" "$namespace" "$kubeconfig_username_ng" "$kube_apiserver_ng1"
config_kubectl "2.ko" "$namespace" "$kubeconfig_username_ko" "$kube_apiserver_ko2"
config_kubectl "2.ng" "$namespace" "$kubeconfig_username_ng" "$kube_apiserver_ng2"

if [ "$testing" = "1" ] ; then

    k8s_login ko_test "$kubeconfig_username_ko_test"

    config_kubectl "test1.ko" "$namespace" "$kubeconfig_username_ko_test" "$kube_apiserver_ko_test"
fi

# set ko1 context for newcomers
context=$(kubectl config current-context 2>&1 || true)
if [[ "$context" == *"current-context is not set" ]]; then
    kubectl config use-context kube1.ko
fi

versions=`kubectl version --short | cut -d' ' -f3 | tr -d "v" | cut -d'.' -f1,2`
# server
kubectl_major_requred=`echo "$versions" | tail -n 1 | cut -d'.' -f1`
kubectl_minor_required=`echo "$versions" | tail -n 1 | cut -d'.' -f2`
# client
kubectl_major=`echo "$versions" | head -n 1 | cut -d'.' -f1`
kubectl_minor=`echo "$versions" | head -n 1 | cut -d'.' -f2`

if [[ "$kubectl_major" -lt ${kubectl_major_requred} ]]; then
    echo "!!!"
    echo "YOUR kubectl IS OLD AS FUCK $kubectl_major.$kubectl_minor (< $kubectl_major_requred.$kubectl_minor_required)"
    echo "!!!"
    echo
else
    minor_diff=$(( kubectl_minor_required-kubectl_minor ))
    if [[ "$kubectl_major" -eq "$kubectl_major_requred"  && $minor_diff -eq 1 ]]; then
        echo "Your kubectl is a little old $kubectl_major.$kubectl_minor (< $kubectl_major_requred.$kubectl_minor_required)"
        echo
    fi
    if [[ "$kubectl_major" -eq "$kubectl_major_requred"  && $minor_diff -gt 1 ]]; then
        echo "!!!"
        echo "Your kubectl is old $kubectl_major.$kubectl_minor (< $kubectl_major_requred.$kubectl_minor_required)"
        echo "!!!"
        echo
    fi
fi
