

class NamespaceWithDefaultValue:
    """
    Argparse namespace class returning `default_value` if attribute is not defined
    """
    def __init__(self, namespace, default_value=None):
        self.namespace = namespace
        self.default_value = default_value

    def __getattr__(self, name):
        if hasattr(self.namespace, name):
            return getattr(self.namespace, name)
        return self.default_value
