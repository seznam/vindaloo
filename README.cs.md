# Vyndá Lů

`Lů` je univerzální vyndavač do kubernetu, který umožňuje snadno pracovat v jednom projektu s více docker registry, docker repozitáři, kubernetes clustery a namespacy, aniž by bylo nutné duplikovat konfiguraci.

Požadavky
---------

Vyžadován je Python 3.6 a vyšší.


Instalace
---------

Stáhnout poslední [binárku](`https://github.com/seznam/vindaloo/raw/master/latest/vindaloo.pex`)

```
sudo wget -O /usr/bin/vindaloo https://github.com/seznam/vindaloo/raw/master/latest/vindaloo.pex
sudo chmod +x /usr/bin/vindaloo
```

nebo přes naší pypi proxy:

```
pip3 install vindaloo
```

Co to umí
---------

- Ubuildit dockerové image
- Pushnout
- deploynout do K8S
- zkontrolovat verze v K8S
- editovat secrety v K8S
- napovídat v bashi

Proč použít právě Lů a ne jiný nástroj
--------------------------------------

- distribuuje se jako jeden spustitelný soubor, netřeba instalace
- konfiguruje se pomocí Pythoních souborů a umožňuje tak velmi malou duplikaci kódu a značnou expresivitu
- umožňuje šablonování pomocí jazyka Mustache (pystache)
- umožňuje includování částí šablon v Dockerfile
- umí z jedné komponenty vybuildit několik docker imagů
- umí měnit kontext pro build docker image
- je téměř kompletně pokrytý testy
- umí napovídat přepínače, prostředí i image použité v komponentě

Konfigurace
-----------

`Lů` používá dvě úrovně konfigurace.

"Globální" konfigurace je očekávána v souboru `vindaloo_conf.py` a definuje
seznam prostředí, jím odpovídající k8s namespacy a seznam k8s clusterů.
`vindaloo_conf.py` je možné umístit přímo do adresáře nasazované komponenty a
nebo do jakéhokoliv nadřazeného adresáře, např. do domovské složky, pokud
používáme pro všechny projekty stejné k8s prostředí (namespacy a clustery).

Každý projekt/komponenta/služba pak obsahuje adresář `k8s`, který obsahuje konfiguraci
pro build a nasazení této komponenty a z ní `Lů`  generuje jednotlivé deploymenty, Dockerfiles, atd.
a ty pak předává `kubectl`.


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

Napovídání v bashi
------------------

Pro zprovoznění napovídání je potřeba přidat do `~/.bashrc`:

```
source <(vindaloo completion)
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
ENVS = {
    'dev': {
        'k8s_namespace': 'avengers-dev',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': 'foo-registry.com',
    },
    'test': {
        'k8s_namespace': 'avengers-test',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': 'foo-registry.com',
    },
    'staging': {
        'k8s_namespace': 'avengers-staging',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': 'foo-registry.com',
    },
    'stable': {
        'k8s_namespace': 'avengers-stable',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': 'foo-registry.com',
    },
}

K8S_CLUSTER_ALIASES = {
    'c1': 'cluster1',
    'c2': 'cluster2',
}
```


Ukázkový base.py
----------------

```
# importujeme verze imagu z versions.json jako slovnik (hnusny hack)
import versions

# bude jen pozit dal
CONFIG = {
    'maintainer': "Pepa Zdepa <pepa@depo.cz>",
    'version': versions['avengers/cool_app'],
    'image_name': 'avengers/coo_app',
}

# Bude jen pouzit dale
DEPLOYMENT = {
    'replicas': 2,
    'ident_label': "cool-app",
    'image': "{}:{}".format(CONFIG['image_name'], CONFIG['version']),
    'container_port': 6666,
    'env': [
        {
            'key': 'BACKEND',
            'val': "some-url.com"
        },
    ]
}

# Bude jen pouzit dale
SERVICE = {
    'app_name': "cool-app",
    'ident_label': "cool-app",
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
            'key': 'BACKEND',
            'val': "some-other-url.com"
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
  "avengers/cool_app": "1.0.0"
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
apiVersion: apps/v1
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

Pokročilejší konfigurace
------------------------

Konfigurace zapsaná v Pythonu umožňuje snadno vyřešit i daleko složitější scénáře.

Můžeme například z jedné komponenty buildit více imagů a ty poté nasazovat v jednom podu - [ukázka konfigurace](examples/multi-image/k8s).

Můžeme také vytvořit soubor podobný crontabu a pomocí něj dynamicky generovat CronJoby.
Navíc pokud bychom potřebovali spustit nějaký skript mimo běžné naplánování, můžeme např. předáním ENV proměnné nasadit jeden Job.

```
DEPLOY_JOB=campaign-run-manager vindaloo deploy dev
```

Více viz [ukázka s cronjoby](examples/cron-jobs/k8s).

Experimentální konfigurace pomocí tříd
--------------------------------------

Kubernetí manifesty mohou být nakonfigurovány použitím slovníků (klasický způsob) nebo tříd (experimentální).
Tato vlastnost není ještě stabilní a měla by být použita jen s opatrností.
Výhodou je, že základ konfigurace může být snadněji měněn v konfigurácích pro jednotlivá prostředí.

Datová struktura použitá ve třídách je v podstatě stejná jako v K8S JSON manifestech, s několika výjimkami.
Všechny `name`, `value` seznamy používané v K8S (např. `env`) jsou uložené jako `key`: `value` pythonní slovníky.

Více v [ukázce](examples/class-config/k8s).

Jak `Lůa` ubuildit
------------------

Nový virtualenv z nějaké rozumně staré trojky.

```
pip install pystache pex

make

# success
```
