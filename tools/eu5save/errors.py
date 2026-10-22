"""Stable exception types for callers; malformed input is never a silent empty save."""
class SaveError(Exception):
    pass


class UnsupportedFormat(SaveError):
    pass


class SaveSyntaxError(SaveError):
    def __init__(self, message, offset=None):
        self.offset = offset
        super().__init__(message + (f' at byte {offset}' if offset is not None else ''))


class SchemaError(SaveError):
    pass


class AmbiguousKey(SchemaError):
    pass


class SourceChanged(SaveError):
    pass
