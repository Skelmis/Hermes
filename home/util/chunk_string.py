def chunk_string(string: str, length: int) -> list[str]:
    return list(string[0 + i : length + i] for i in range(0, len(string), length))


def inject_spaces_into_string(string: str, length: int = 20) -> str:
    return " ".join(chunk_string(string, length))
