
class UnknownObject(Exception):
    def __init__(self, obj):
        super().__init__(f"Unknown object: {obj}")

class UnknownOperator(Exception):
    def __init__(self, operator):
        super().__init__(f"Unknown operator: {operator}")

class UnknownType(Exception):
    def __init__(self, raw):
        super().__init__(f"Invalid type: {raw}")

class UnexpectedToken(Exception):
    def __init__(self, token):
        super().__init__(f"Unexpected token: {token}")

class UnexpectedEOF(Exception):
    def __init__(self):
        super().__init__(f"Unexpected EOF")

class UnmatchedBrackets(Exception):
    def __init__(self):
        super().__init__(f"Unmatched bracket")

class WeavedBrackets(Exception):
    def __init__(self):
        super().__init__(f"Weaved brackets")