
class UnknownObjectError(Exception):
    def __init__(self, obj):
        super().__init__(f"Unknown object: {obj}")

class UnknownOperatorError(Exception):
    def __init__(self, operator):
        super().__init__(f"Unknown operator: {operator}")

class UnknownTypeError(Exception):
    def __init__(self, raw):
        super().__init__(f"Invalid type: {raw}")

class UnexpectedTokenError(Exception):
    def __init__(self, token):
        super().__init__(f"Unexpected token: {token}")

class UnexpectedEOFError(Exception):
    def __init__(self):
        super().__init__(f"Unexpected EOF")

class UnmatchedBracketsError(Exception):
    def __init__(self):
        super().__init__(f"Unmatched bracket")

class WeavedBracketsError(Exception):
    def __init__(self):
        super().__init__(f"Weaved brackets")