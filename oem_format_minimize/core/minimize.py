from copy import deepcopy
import inspect


class MinimizeProtocol(object):
    __built = False
    __encode_map = {}
    __protocols = {}

    __key__ = None

    __ignore__ = False
    __process__ = None
    __root__ = False
    __version__ = None

    @classmethod
    def build(cls):
        if cls.__built:
            return

        cls.__decode_map = {}
        cls.__encode_map = {}

        cls.__protocols = {}

        for key in dir(cls):
            value = getattr(cls, key)

            if key.startswith('__') or key.startswith('_MinimizeProtocol__') or inspect.ismethod(value):
                continue

            if type(value) is int:
                cls.__decode_map[value] = key
                cls.__encode_map[key] = value
            elif inspect.isclass(value):
                cls.__protocols[value.__key__] = value
            else:
                raise ValueError('Unknown property in protocol (key: %r)' % key)

        cls.__built = True

    @classmethod
    def get_protocol(cls, name):
        if name not in cls.__protocols:
            raise ValueError('Missing definition in %r for protocol %r' % (cls, name))

        return cls.__protocols[name]

    @classmethod
    def decode_key(cls, key):
        # Ensure `key` is an integer
        if type(key) is not int:
            key = int(key)

        # Try retrieve decode mapping for `key`
        if key not in cls.__decode_map:
            raise ValueError('Missing definition in %r for key %r' % (cls, key))

        return cls.__decode_map[key]

    @classmethod
    def encode_key(cls, key):
        if key not in cls.__encode_map:
            raise ValueError('Missing definition in %r for key %r' % (cls, key))

        return cls.__encode_map[key]

    @classmethod
    def get_value(cls, data, key, default=None):
        try:
            return data[str(key)]
        except KeyError:
            try:
                return data[key]
            except KeyError:
                return default

    @classmethod
    def to_child(cls, key=None, process=None):
        if process is not None:
            if type(process) is not dict:
                raise ValueError('Invalid value provided for "process" parameter, expected a dictionary')

            if cls.__process__:
                # Merge class `__process__` parameters with provided parameters
                result = {}
                result.update(deepcopy(cls.__process__))
                result.update(process)

                process = result

        class Child(cls):
            __key__ = key

            __process__ = process
            __root__ = False

        Child.__name__ = cls.__name__
        return Child


class Minimize(object):
    @classmethod
    def decode(cls, data, protocol, process=None):
        if protocol.__ignore__:
            return data

        # Pre-process `data`
        processed, result = cls._process(
            data, protocol,
            func=cls.decode,
            process=process
        )

        if processed:
            return result

        # Ensure protocol is built
        protocol.build()

        # Process each item in `data`
        result = {}

        for key, value in data.items():
            # Ignore "minimized" item identifier
            if key == '~':
                continue

            # Decode `key` with `protocol`
            key = protocol.decode_key(key)

            # Process child protocols
            if type(value) is dict:
                # Decode `value` with `protocol`
                value = cls.decode(value, protocol.get_protocol(key))
            elif type(value) is list:
                # Decode items in `value` with `protocol`
                value = [
                    (
                        cls.decode(value, protocol.get_protocol(key))
                        if type(value) is dict else value
                    )
                    for value in value
                ]

            # Store item
            result[key] = value

        return result

    @classmethod
    def encode(cls, data, protocol, process=None):
        if protocol.__ignore__:
            return data

        # Pre-process `data`
        processed, result = cls._process(
            data, protocol,
            func=cls.encode,
            process=process
        )

        if processed:
            return result

        # Ensure protocol is built
        protocol.build()

        # Process each item in `data`
        result = {}

        for key, value in data.items():
            # Process child protocols
            if type(value) is dict:
                # Encode `value` with `protocol`
                value = cls.encode(value, protocol.get_protocol(key))
            elif type(value) is list:
                # Encode items in `value` with `protocol`
                value = [
                    (
                        cls.encode(value, protocol.get_protocol(key))
                        if type(value) is dict else value
                    )
                    for value in value
                ]

            # Encode `key` with `protocol`
            key = protocol.encode_key(key)

            # Store item
            result[key] = value

        if protocol.__root__:
            if protocol.__version__ is None:
                raise ValueError('Missing "__version__" parameter on %r' % protocol)

            # Set "minimize" flag (and version)
            result['~'] = protocol.__version__

        return result

    @classmethod
    def _process(cls, data, protocol, func, process=None):
        # Retrieve parameters
        mode, optional, supported = cls._process_parameters(protocol, process)

        # Pre-process `data`
        if mode == 'children':
            # Process dictionary of children
            if type(data) is dict and (supported is None or type(data) in supported):
                return True, dict([
                    (key, func(value, protocol, process='item'))
                    for key, value in data.items()
                ])

            # Process list of children
            if type(data) is list and (supported is None or type(data) in supported):
                return True, [
                    func(value, protocol, process='item')
                    for value in data
                ]

            if not optional:
                raise ValueError('Dictionary or List required for %r protocol' % protocol)
        elif mode == 'item':
            # Process dictionary of item children
            if type(data) is dict and supported and type(data) in supported:
                return True, dict([
                    (key, func(value, protocol, process='item'))
                    for key, value in data.items()
                ])

            # Process list of item children
            if type(data) is list and supported and type(data) in supported:
                return True, [
                    func(value, protocol, process='item')
                    for value in data
                ]

        # No processing required
        return False, None

    @classmethod
    def _process_parameters(cls, protocol, process):
        mode = None

        if process is None:
            process = protocol.__process__

            if type(process) is dict and process and 'children' in process:
                mode = 'children'

                if type(process) is not bool:
                    process = process['children']
            elif type(process) is str:
                mode = process
            elif process:
                raise ValueError

        if type(process) is str:
            if type(protocol.__process__) is dict and process in protocol.__process__:
                mode = process
                process = protocol.__process__[process]
            else:
                mode = process

        # Retrieve parameters
        if type(process) is dict:
            return (
                mode or process.get('mode'),
                process.get('optional', False),
                process.get('supported')
            )

        return (
            mode or process,
            False,
            None
        )
