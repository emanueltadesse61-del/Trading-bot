"""Named registry failures."""


class RegistryError(ValueError):
    def __init__(self, code, detail=None):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail is not None else code)
