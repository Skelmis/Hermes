import asyncio
import hashlib
import logging

import commons
import httpx

log = logging.getLogger(__name__)


async def has_password_been_pwned(password: str) -> bool:
    """Lookup the password in have i been pwned

    Returns
    -------
    bool
        True if pwned, false in all other cases

    Warnings
    --------
    Fails safely in the sense that a failed
    lookup won't block a login attempt
    """
    password_hash = hashlib.sha1(password.encode()).hexdigest().upper()
    first_chars = password_hash[:5]
    remaining_chars = password_hash[5:]
    assert first_chars + remaining_chars == password_hash
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{first_chars}",
                timeout=5,
            )
    except Exception as e:
        log.critical(
            "Pwned passwords lookup failed:\n%s", commons.exception_as_string(e)
        )
        return False

    if remaining_chars in response.text:
        return True

    return False


async def main():
    print(await has_password_been_pwned("test"))
    print(await has_password_been_pwned("qwerty"))
    print(await has_password_been_pwned("fbghbdajkwdjkwadkwadjkwad"))


if __name__ == "__main__":
    asyncio.run(main())
