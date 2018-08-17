import asyncio


# by default, there's a limit of ~1MB. our payloads can be much larger than
# that, if transferring images, so let's just turn the limit off
MAX_PAYLOAD_SIZE = None


KEEPALIVE_INTERVAL_SECONDS = 30


# when running clipshare behind nginx, the server and client would seem to get
# disconnected frequently. at least on dokku's settings. adding this keepalive
# fixes the problem there. it's probably good to keep this in here. i bet it'll
# help with other configurations as well.
async def keepalive_forever(websocket):
    while True:
        await asyncio.sleep(KEEPALIVE_INTERVAL_SECONDS)
        await websocket.ping()
