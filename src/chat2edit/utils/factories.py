from uuid import uuid4


def uuid4_factory() -> str:
    return str(uuid4())
