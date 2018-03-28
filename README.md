sostool
=======
Cilem je vytvorit univerzalni deploy tool na kuberneti veci.
Tohle je takovy maly experiment na zadane tema, uvidime jstli to chceme
a jesti to chceme takhle :-)
Myslenka je takova, ze v adresari k8s budeme v kazdem projektu mit konfiguraci
v pythonim formatu a z ni budeme generovat jednotlive deploymenty, Dockerfiles
a ty pak deployovat.

Co to umi
---------
Zatim jen maly zaklad

- Ubuildit dockerove image
- Pushnout 
- zkontrolovat verze v K8S
- prihlasit se do clusteru
- deploynout do clusteru, jen selektivne zmenene

 
Typycke pouziti
---------------

```
cd /projekt  (musi obsahovat adresar k8s)
sostool.pex versions
```

Hilfe
-----

```
./sostool <command> [options, ...]


build - ubali Docker image (vsechny)

push - pushne docker image (vsechny)

versions - vypise verze vsech imagu a srovna s clusterem

kubelogin <ko|ng> - prihlasi se do kubernetu

deploy <env> - nasadi zmeny do clusteru
```

Struktura K8S
-------------
Prvni priklad je v groupware bridge. (zatim ve vetvi new_kube)

Kazdopadne se drzime tohoto:

```
k8s
    templates
        - Dockerfile
        - deployment.yaml
        - some_other.yaml
    
    - base.py
    - test.py
    - dev.py
    - stage.py
    - prod.py
```

`templates` obsahuje sablony generovanych souboru. Uvnitr maji mustache syntaxi.
Dovoluje i jednoduche cyckly atp. Je to takovy neseznami TENG :-) 
Syntaxe: https://mustache.github.io/mustache.5.html

`base.py` je zaklad konfigurace a mel by obsahovat to co budou mit spolecne
konfigurace pro vsechna prostredi.

`[dev/test/...].py` jsou konfiguraky pro jednotliva prostredi a obsahuji veci specificke.


Ukazkovy base.py
----------------

```

# bude jen pozit dal
CONFIG_FRAGMENT_FRAGMENT = {
    'maintainer': "Viktor Lacina <viktor.lacina@firma.seznam.cz>",
    'version': "1.29.0",
    'image_name': 'doc.ker.dev/sos/groupware_bridge'
}

# Bude jen pouzit dale
DEPLOYMENT_FRAGMENT = {
    'file_version': 1,
    'replicas': 2,
    'ident_label': "groupware-bridge",
    'image': "{}:{}".format(CONFIG_FRAGMENT['image_name'], CONFIG_FRAGMENT['version']),
    'container_port': 6666,
    'env': [
        {
            'key': 'EXCHANGE_SERVER',
            'val': "posta.szn.cz"
        },
    ]
}

# Bude jen pouzit dale
SERVICE_FRAGMENT = {
    'file_version': 4,
    'app_name': "groupware-bridge",
    'ident_label': "groupware-bridge-service",
    'port': 31666,
}

# Konfigurace docker files
# pole dictu s klici:
# dir - adresar kam ma byt vygenerovan Dockerfile
# config - dict s konfiguraci
# template - soubor se sablonou dockerfile z templates
DOCKER_FILES = [
    {
        'dir': ".",
        'config': CONFIG_FRAGMENT,
        'template': "Dockerfile",
    }
]

# Popis deploy yamlu, podobne jako docker files
# navic je tu object_type, ktery obsahuje typ yamlu, keywordy stejne jako k8s
# V kazdem configu musi byt ident_label a file_version
K8S_OBJECTS = {
    "deployment": [
        {
            'dir': "k8s",
            'config': DEPLOYMENT_FRAGMENT,
            'template': "deployment.yaml",
            'object_type': "deployment"
        },
    ],
    "service": [
        {
            'dir': "k8s",
            'config': SERVICE_FRAGMENT,
            'template': "service.yaml",
            'object_type': "service",
        },
    ]
}
```

Ukazkovy dev.py
----------------

```
from base import *  #  Tim podedime konfiguraci


# Tady muzeme prekryt, nebo modifikovat cokoliv, co je nadefinovano v BASE


DEDPLOYMENT_FRAGMENT.update({
    'novy_klic': 'nova_hodnota'
})

```