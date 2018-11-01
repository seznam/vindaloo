# Vyndá Lů

`Lů` je univerzální vyndavač do kubernetu, který umožňuje snadno pracovat v jednom projektu s více docker registry, docker repozitáři, kubernetes clustery a namespacy, aniž by bylo nutné duplikovat konfiguraci.

`Lů` používá dvě úrovně konfigurace.

"Globální" konfigurace je očekávána v souboru `vindaloo_conf.py` a definuje
seznam prostředí, jím odpovídající k8s namespacy a seznam k8s clusterů.
`vindaloo_conf.py` je možné umístit přímo do adresáře nasazované komponenty a
nebo do jakéhokoliv nadřazeného adresáře, např. do domovské složky, pokud
používáme pro všechny projekty stejné k8s prostředí (namespacy a clustery).

Každý projekt/komponenta/služba pak obsahuje adresář `k8s`, který obsahuje konfiguraci
pro build a nasazení této komponenty a z ní `Lů`  generuje jednotlivé deploymenty, Dockerfiles, atd.
a ty pak předává `kubectl`.

Požadavky
---------

Vyžadován je Python 3.5 a vyšší.


Instalace
---------

Stáhnout poslední [binárku](`https://vindaloo.dev.dszn.cz/vindaloo.pex`)

```
sudo wget --no-check-certificate -O /usr/bin/vindaloo https://vindaloo.dev.dszn.cz/vindaloo.pex
sudo chmod +x /usr/bin/vindaloo
```

Co to umí
---------

- Ubuildit dockerové image
- Pushnout
- deploynout do K8S
- zkontrolovat verze v K8S
- přihlásit se do clusteru

Proč použít právě Lů a ne jiný nástroj
--------------------------------------

- distribuuje se jako jeden spustitelný soubor, netřeba instalace
- konfiguruje se pomocí Pythoních souborů a umožňuje tak velmi malou duplikaci kódu a značnou expresivitu
- umožňuje šablonování pomocí jazyka Mustache (pystache)
- umožňuje includování částí šablon v Dockerfile
- umí z jedné komponenty vybuildit několik docker imagů
- umí měnit kontext pro build docker image
- je téměř kompletně pokrytý testy


Typycké použití
---------------

```
cd projekt  
vindaloo init .

vindaloo build
vindaloo push
vindaloo deploy dev ko
vindaloo deploy dev ng

vindaloo versions
```

Hilfe
-----

```
usage: vindaloo [-h] [--debug] [--noninteractive] [--quiet] [--dryrun]
                {init,build,pull,push,kubeenv,versions,kubelogin,deploy,build-push-deploy}
                ...

Nastroj pro usnadneni prace s dockerem a kubernetes

optional arguments:
  -h, --help            show this help message and exit
  --debug
  --noninteractive      Na nic se nepta
  --quiet               Potlaci vystup
  --dryrun              Jen predstira, nedela zadne nevratne zmeny

commands:
  {init,build,pull,push,kubeenv,versions,kubelogin,deploy,build-push-deploy}
    init                pripravi projekt pro praci s Vindaloo
    build               ubali Docker image (vsechny)
    pull                pullne docker image (vsechny)
    push                pushne docker image (vsechny)
    kubeenv             switchne aktualni kubernetes context v ENV
    versions            vypise verze vsech imagu a srovna s clusterem
    kubelogin           prihlasi se do kubernetu
    deploy              nasadi zmeny do clusteru
    build-push-deploy   udela vsechny tri kroky
```

Konfigurace projektu
--------------------

```
vindaloo_conf.py
k8s
    templates
        - Dockerfile
        - deployment.yaml
        - service.yaml

    - base.py
    - dev.py
    - test.py
    - stable.py
    - versions.json
```

`vindaloo_conf.py` obsahuje definici běhových prostředí (dev, test, stable), jím odpovídající k8s namespacy a seznam k8s clusterů,
do kterých budeme nasazovat.
Soubor může být umístěn v adresáří komponenty nebo kdekoliv výše (pokud konfiguraci sdílíme napříč více komponentami).

Konfigurace deploymentu komponenty je umístěna ve složce `k8s`, kde najdeme několik souborů a složku:

`templates` obsahuje šablony generovaných souborů. Uvnitř mají mustache syntaxi.
Dovoluje i jednoduché cyckly atp. Je to takový neseznamý TENG :-)
Syntaxe: https://mustache.github.io/mustache.5.html

`base.py` je základ konfigurace a měl by obsahovat to, co budou mít společné
konfigurace pro všechna prostředí.

`[dev/test/...].py` jsou konfiguráky pro jednotlivá prostředí a obsahují věci pro ně specifické (např. nodePorty).

`versions.json` je konfigurák definující verze imagů, které chceme buildit/nasadit.
Jelikož je to JSON, můžeme ho snadno číst i zapisovat programově.


Ukázkový vindaloo_conf.py
-------------------------

```
# konstanty pro prostredi
DEV = "dev"
TEST = "test"
PRERELEASE = "prerelease"
STAGING = "staging"
STABLE = "stable"

# seznam prostredi, ktera chceme pouzivat
LOCAL_ENVS = [DEV, TEST, PRERELEASE, STAGING, STABLE]

# odpovidajici k8s namespacy
K8S_NAMESPACES = {
    DEV: "sos-dev",
    TEST: "sos-test",
    PRERELEASE: "sos-pre-release",
    STAGING: "sos-staging",
    STABLE: "sos-stable",
}

# seznam k8s clusteru
K8S_CLUSTERS = {
    "ko": "kube1.ko",
    "ng": "kube1.ng",
}

# seznam prostredi, pro ktera chceme pouzivat produkcni docker registry
ENVS_WITH_PROD_REGISTRY = [STAGING, STABLE]
```


Ukázkový base.py
----------------

```
# importujeme verze imagu z versions.json jako slovnik (hnusny hack)
import versions

# bude jen pozit dal
CONFIG = {
    'maintainer': "Viktor Lacina <viktor.lacina@firma.seznam.cz>",
    'version': versions['sos/groupware_bridge'],
    'image_name': 'sos/groupware_bridge',
}

# Bude jen pouzit dale
DEPLOYMENT = {
    'replicas': 2,
    'ident_label': "groupware-bridge",
    'image': "{}:{}".format(CONFIG['image_name'], CONFIG['version']),
    'container_port': 6666,
    'env': [
        {
            'key': 'EXCHANGE_SERVER',
            'val': "posta.szn.cz"
        },
    ]
}

# Bude jen pouzit dale
SERVICE = {
    'app_name': "groupware-bridge",
    'ident_label': "groupware-bridge",
    'container_port': 6666,
    'port': 31666,
}

# Konfigurace docker files
# pole dictu s klici:
# context_dir - adresar ktery se preda dockeru
# config - dict s konfiguraci
# template - soubor se sablonou dockerfile z templates
# pre_build_msg - hlaska, ktera se zobrazi pred spustenim buildu
# includes - volitelne includy souboru, na kazdem bude take zavolan mustache se stejnym
             kontextem, jako hlavni sablona. Podle promenne je pak mozne vlozit do hlavni
             sablony.
DOCKER_FILES = [
    {
        'context_dir': ".",
        'config': CONFIG,
        'template': "Dockerfile",
        'pre_build_msg': """Prosim nejdriv spust:

make clean
"""
        'includes': {  # Nepovinne
             'promenna': 'cesta/k/souboru/se/sablonou',
        }
    }
]

# Popis deploy yamlu, podobne jako docker files
K8S_OBJECTS = {
    "deployment": [
        {
            'config': DEPLOYMENT,
            'template': "deployment.yaml",
        },
    ],
    "service": [
        {
            'config': SERVICE,
            'template': "service.yaml",
        },
    ]
}
```

Ukázkový dev.py
----------------

```
from base import *  #  Tim podedime konfiguraci

# Tady muzeme prekryt, nebo modifikovat cokoliv, co je nadefinovano v base.py


DEPLOYMENT.update({
    'env': [
        {
            'key': 'EXCHANGE_SERVER',
            'val': "posta.dev.dszn.cz"
        },
    ]
})

SERVICE.update({
    'port': 32666,
})
```

Ukázkový versions.json
----------------------

```
{
  "sos/groupware_bridge": "1.0.0"
}
```


Ukázkový Dockerfile
-------------------

```
{{#includes}}{{&base_image}}{{/includes}}
LABEL maintainer="{{{maintainer}}}"
LABEL description="SOS adminweb"

COPY ...
RUN ...
CMD ...

LABEL version="{{version}}"
```

Ukázkový deployment.yaml
------------------------

```
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: {{ident_label}}
spec:
  replicas: {{replicas}}
  template:
    metadata:
      name: {{ident_label}}
      labels:
        app: {{ident_label}}
    spec:
      containers:
      - name: {{ident_label}}
        image: {{registry}}/{{image}}
        ports:
        - containerPort: {{container_port}}
        livenessProbe:
          initialDelaySeconds: 5
          periodSeconds: 5
          httpGet:
            path: /
            port: {{container_port}}
```

Ukázkový service.yaml
------------------------

```
apiVersion: v1
kind: Service
metadata:
  name: {{ident_label}}
  labels:
    name: {{ident_label}}
spec:
  type: NodePort
  ports:
  - name: http
    nodePort: {{port}}
    port: {{container_port}}
    protocol: TCP
  selector:
    app: {{app_name}}
```

Ukázky složitější konfigurace:
- [s builděním několika imagů](examples/multi-image/k8s)
- [s generovanými CronJoby](examples/cron-jobs/k8s)

Jak `Lůa` ubuildit
------------------

Nový virtualenv z nějaké rozumně staré trojky.

```
pip install pystache pex

make

# success
```
