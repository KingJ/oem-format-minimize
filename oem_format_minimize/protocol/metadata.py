from oem_format_minimize.core.minimize import MinimizeProtocol


class MetadataMinimizeProtocol(MinimizeProtocol):
    __root__ = True

    revision    = 0x01
    hashes      = 0x02

    media       = 0x03

    class HashesProtocol(MinimizeProtocol):
        __key__ = 'hashes'
        __ignore__ = True
