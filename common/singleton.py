def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        singleton_key = kwargs.pop("_singleton_key", None)
        cache_key = (cls, singleton_key) if singleton_key else cls
        if cache_key not in instances:
            instances[cache_key] = cls(*args, **kwargs)
        return instances[cache_key]

    return get_instance
