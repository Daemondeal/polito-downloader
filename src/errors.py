class ApiException(Exception):
    code: int

    def __init__(self, message="", code=400):
        super().__init__(self, message)
        self.code = code
