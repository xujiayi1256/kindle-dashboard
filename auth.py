import time

import jwt

import config


def get_qweather_token() -> str:
    """Return a valid QWeather JWT for API requests."""
    if config.JWT_TOKEN:
        return config.JWT_TOKEN

    if not all([config.KID, config.PROJECT_ID, config.PRIVATE_KEY]):
        raise RuntimeError(
            "Missing QWeather credentials. Set QWEATHER_JWT, or set "
            "QWEATHER_KID + QWEATHER_PROJECT_ID + QWEATHER_PRIVATE_KEY."
        )

    private_key = config.PRIVATE_KEY.replace("\\n", "\n")
    now = int(time.time())
    payload = {
        "sub": config.PROJECT_ID,
        "iat": now - 30,
        "exp": now + 900,
    }
    headers = {"alg": "EdDSA", "kid": config.KID}
    return jwt.encode(payload, private_key, algorithm="EdDSA", headers=headers)
