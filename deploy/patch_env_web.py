"""Patch the server .env.prod for the web terminal (idempotent)."""

from pathlib import Path

ENV = Path.home() / 'aegis-trader' / '.env.prod'
CORS = 'CORS_ORIGINS=["https://traderbackend.awesometech.com.ng","https://trader.awesometech.com.ng"]'

lines = ENV.read_text().splitlines()
patched: list[str] = []
for line in lines:
    if line.startswith('CORS_ORIGINS='):
        patched.append(CORS)
    else:
        patched.append(line)

text = '\n'.join(patched)
if 'WEB_HOST_PORT=' not in text:
    text += (
        '\nWEB_HOST_PORT=9077'
        '\nNUXT_PUBLIC_API_BASE_URL=https://traderbackend.awesometech.com.ng'
        '\nNUXT_PUBLIC_WS_BASE_URL=wss://traderbackend.awesometech.com.ng'
    )
ENV.write_text(text.rstrip('\n') + '\n')
print('patched .env.prod')
