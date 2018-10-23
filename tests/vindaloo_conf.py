DEV = "dev"
TEST = "test"
STAGING = "staging"
STABLE = "stable"

LOCAL_ENVS = [DEV, TEST, STAGING, STABLE]

K8S_NAMESPACES = {
    DEV: "foo-dev",
    TEST: "foo-test",
    STAGING: "foo-staging",
    STABLE: "foo-stable",
}

K8S_CLUSTERS = {
    "ko": "kube1.ko",
    "ng": "kube1.ng",
}

ENVS_WITH_PROD_REGISTRY = [STAGING, STABLE]
