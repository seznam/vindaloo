DEV_REGISTRY = 'foo-registry.com'
PROD_REGISTRY = 'foo-prog-registry.com'

ENVS = {
    'dev': {
        'k8s_namespace': 'foo-dev',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': DEV_REGISTRY,
    },
    'test': {
        'k8s_namespace': 'foo-test',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': DEV_REGISTRY,
    },
    'staging': {
        'k8s_namespace': 'foo-staging',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': PROD_REGISTRY,
    },
    'stable': {
        'k8s_namespace': 'foo-stable',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': PROD_REGISTRY,
    },
}

K8S_CLUSTER_ALIASES = {
    'c1': 'cluster1',
    'c2': 'cluster2',
}
