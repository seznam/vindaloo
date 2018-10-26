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
