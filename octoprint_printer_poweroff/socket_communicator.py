import asyncio

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager


class SocketCommunicator():
    def __init__(self, name, email, password, delay, logger):
        self._name = name
        self._email = email
        self._password = password
        self._delay = delay
        self._logger = logger

    async def power_off(self):
        http_api_client = await MerossHttpClient.async_from_user_password(email=self._email, password=self._password)
        manager = MerossManager(http_client=http_api_client)
        await manager.async_init()

        await manager.async_device_discovery()
        plugs = manager.find_devices(device_name=self._name)

        if len(plugs) < 1:
            self._logger("No killswitch found...")
        else:
            dev = plugs[0]
            await dev.async_update()
            self._logger("Turning printer off...")
            await asyncio.sleep(self._delay)
            await dev.async_turn_off(channel=0)

        manager.close()
        await http_api_client.async_logout()
