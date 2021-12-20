from __future__ import absolute_import, unicode_literals
import asyncio

import octoprint

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager


device_name = ""
meross_email = ""
meross_password = ""

DEFAULT_MAX_EXTRUDER_TEMP = 300
DEFAULT_MAX_BED_TEMP = 80

max_extruder_temp = DEFAULT_MAX_EXTRUDER_TEMP
max_bed_temp = DEFAULT_MAX_BED_TEMP

lock = asyncio.Lock()


class SocketCommunicator():
    def __init__(self, name, email, password, delay, logger, retry=True):
        self._name = name
        self._email = email
        self._password = password
        self._delay = delay
        self._logger = logger
        self._retry = retry

    async def power_off(self):
        if lock.locked():
            self._logger("Power off is already in progress, skipping...")
            return

        await lock.acquire()

        try:
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

        except:
            if not self._retry:
                return
            self._logger("Error during powering off, retrying...")
            await asyncio.sleep(2)
            await self.power_off()

        finally:
            lock.release()


class PowerOffPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.EventHandlerPlugin,
):
    def get_settings_defaults(self):
        return dict(
            device_name="name",
            meross_email="email",
            meross_password="password",
            power_off_delay=5,
            max_extruder_temp=DEFAULT_MAX_EXTRUDER_TEMP,
            max_bed_temp=DEFAULT_MAX_BED_TEMP,
            enabled=False
        )

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=False)]

    def on_event(self, event, payload):
        if event == "PrintDone" or (event == "PrintFailed" and payload["reason"] == "error"):
            self._logger.info("Shutting down. Reason: " + event)

            if not self._settings.get(["enabled"]):
                return

            asyncio.run(
                SocketCommunicator(
                    self._settings.get(["device_name"]),
                    self._settings.get(["meross_email"]),
                    self._settings.get(["meross_password"]),
                    int(self._settings.get(["power_off_delay"])),
                    self._logger.info
                ).power_off())

    def update_global_params(self):
        global max_extruder_temp
        global max_bed_temp
        global device_name
        global meross_email
        global meross_password
        max_extruder_temp = int(self._settings.get(["max_extruder_temp"]))
        max_bed_temp = int(self._settings.get(["max_bed_temp"]))
        device_name = self._settings.get(["device_name"])
        meross_email = self._settings.get(["meross_email"])
        meross_password = self._settings.get(["meross_password"])

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.update_global_params()

    def on_after_startup(self):
        self.update_global_params()


def temperature_guard(comm, parsed_temps):
    if not 'B' in parsed_temps or not 'T0' in parsed_temps:
        print("Can not find correct temperature keys, skipping...")
        return
    actual_bed_temp = int(parsed_temps['B'][0])
    actual_extruder_temp = int(parsed_temps['T0'][0])
    if (actual_bed_temp > max_bed_temp) or (actual_extruder_temp > max_extruder_temp):
        print("Owerheated, shutting down...")
        asyncio.run(
            SocketCommunicator(
                device_name,
                meross_email,
                meross_password,
                1,
                print,
                False
            ).power_off())

    return parsed_temps


__plugin_name__ = "Printer Power Off"
__plugin_version__ = "0.1.1"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = PowerOffPlugin()
__plugin_hooks__ = {
    "octoprint.comm.protocol.temperatures.received": temperature_guard
}
