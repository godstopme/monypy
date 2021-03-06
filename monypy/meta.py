import copy

from bson.codec_options import DEFAULT_CODEC_OPTIONS

from .connection import connect
from .manager import Manager, ManagerDescriptor

DOC_DATA = '#data'

DOC_INIT_DATA = '__init_data__'
DOC_DATABASE = '__database__'
DOC_LOOP = '__loop__'


class DocMeta(type):
    def __new__(mcs, name, bases, clsargs):
        database = None
        loop = None

        if DOC_DATABASE in clsargs:
            database = clsargs.pop(DOC_DATABASE)
            loop = clsargs.pop(DOC_LOOP, None)

        cls = super().__new__(mcs, name, bases, clsargs)

        if database:
            client = connect(
                host=database['host'],
                port=database['port'],
                io_loop=loop
            )

            assert 'name' in database

            base = client[database['name']]

            collection_name = database.get('collection', name.lower())
            collection_codec_options = DEFAULT_CODEC_OPTIONS.with_options(document_class=cls)
            collection = base[collection_name].with_options(collection_codec_options)

            cls.manager = manager_factory(cls, collection)

        return cls

    def __call__(cls, *args, **kwargs):
        init_data = copy.deepcopy(
            args[0] if args else kwargs
        )

        assert isinstance(init_data, dict)

        instance = super().__call__()
        instance.__dict__[DOC_DATA] = {}

        defaults = copy.deepcopy(
            getattr(instance, DOC_INIT_DATA, {})
        )
        defaults.update(init_data)

        for k, v in defaults.items():
            if callable(v):
                defaults[k] = v(instance)

        instance.__dict__[DOC_DATA].update(defaults)

        return instance


def manager_factory(doc_class, collection):
    manager_doc_class = doc_class.manager_class
    manager_class = (manager_doc_class.for_doc(doc_class)
                     if manager_doc_class is Manager
                     else manager_doc_class)

    manager = manager_class(collection)
    return ManagerDescriptor(manager)
