""" Update Cloudflare DNS with new ip

    Keeps one Cloudflare A record equal to your public IP address. The IP comes from a
    Home Assistant sensor (ip_sensor) or, without one, from an IP service once an hour.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.1"

import ipaddress
import json

from appdaemon import adbase as ad
import aiohttp

RETRY_SECONDS = 900
RETRY_MAX = 6
REQUEST_TIMEOUT = 20


class Change_DNS(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')

        self.public_ip:str | None = None
        self.cloudflare_ip:str | None = None
        self.record_name:str | None = None
        self.updating:bool = False
        self.wrong_record_type:bool = False
        # None keeps the proxy setting that the record has in Cloudflare
        self.proxy:bool | None = self.args.get('enable_proxy', None)
        self.ip_check_url:str = self.args.get('ip_check_url', 'https://api.ipify.org')

        self.cloudflare_api_token = self.args['cloudflare_api_token']
        self.zone_id = self.args['zone_id']
        self.dns_record_id = self.args['dns_record_id']

        self.headersList = {
          "Accept": "*/*",
          "Authorization": "Bearer " + str(self.cloudflare_api_token)
          }
        self.reqUrl = "https://api.cloudflare.com/client/v4/zones/" + str(self.zone_id) + "/dns_records/" + str(self.dns_record_id)

        self.ip_sensor = self.args.get('ip_sensor', None)
        if self.ip_sensor is not None:
            self.ADapi.listen_state(self._ha_DNS_ip_sensor_changed, self.ip_sensor,
                namespace = self.HASS_namespace
            )
        else:
            self.ADapi.run_hourly(self._checkPublicIPAddress, "00:10:00")

        self.ADapi.create_task(self._startup())

    async def _startup(self) -> None:
        """ Reads the record in Cloudflare and the public IP, and updates the record if they differ. """

        await self._get_current_DNS()
        if self.ip_sensor is not None:
            # API calls inside a coroutine have to be awaited
            self.public_ip = self._valid_ipv4(await self.ADapi.get_state(self.ip_sensor, namespace = self.HASS_namespace))
        else:
            self.public_ip = await self._get_public_ip()
        await self._sync()

    def _valid_ipv4(self, value) -> str | None:
        """ Returns the value if it is an IPv4 address (the only thing an A record can hold). """

        try:
            return str(ipaddress.IPv4Address(str(value).strip()))
        except ValueError:
            return None

    def _ha_DNS_ip_sensor_changed(self, entity, attribute, old, new, kwargs) -> None:
        if new in (None, 'unavailable', 'unknown'):
            return
        new_ip = self._valid_ipv4(new)
        if new_ip is None:
            self.ADapi.log(f"{self.name}: {entity} state '{new}' is not an IPv4 address.", level='WARNING')
            return
        self.public_ip = new_ip
        self.ADapi.create_task(self._sync())

    def _checkPublicIPAddress(self, kwargs) -> None:
        self.ADapi.create_task(self._poll())

    async def _poll(self) -> None:
        public_ip = await self._get_public_ip()
        if public_ip is not None:
            self.public_ip = public_ip
            await self._sync()

    async def _get_public_ip(self) -> str | None:
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.ip_check_url) as response:
                    if 200 <= response.status < 300:
                        result = self._valid_ipv4(await response.text())
                        if result is None:
                            self.ADapi.log(f"{self.name}: {self.ip_check_url} did not return an IPv4 address.", level='WARNING')
                        return result
                    self.ADapi.log(
                        f"{self.name}: Not able to get IP from {self.ip_check_url}. Status: {response.status}.",
                        level='WARNING'
                    )
        except Exception as e:
            self.ADapi.log(f"{self.name}: Not able to get IP from {self.ip_check_url}. Exception: {e}", level='WARNING')
        return None

    async def _get_current_DNS(self) -> None:
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.reqUrl, headers=self.headersList) as response:
                    if 200 <= response.status < 300:
                        result = json.loads(await response.text())['result']
                        if result.get('type', 'A') != 'A':
                            self.ADapi.log(
                                f"{self.name}: dns_record_id is a {result.get('type')} record. Only A records are updated.",
                                level='ERROR'
                            )
                            self.wrong_record_type = True
                            return
                        self.cloudflare_ip = self._valid_ipv4(result['content'])
                        self.record_name = result['name']
                    else:
                        self.ADapi.log(
                            f"{self.name}: Not able to get the record from Cloudflare. Status: {response.status}.",
                            level='WARNING'
                        )
        except Exception as e:
            self.ADapi.log(f"{self.name}: Not able to get the record from Cloudflare. Exception: {e}", level='WARNING')

    async def _sync(self, tries:int = 0) -> None:
        """ Updates Cloudflare if the record is not equal to the public IP. """

        if self.updating or self.public_ip is None or self.wrong_record_type:
            return
        self.updating = True
        try:
            if self.cloudflare_ip is None:
                await self._get_current_DNS()
            if self.cloudflare_ip is None or self.cloudflare_ip == self.public_ip:
                return
            updated = await self._updateDNS()
        finally:
            self.updating = False
        if not updated and tries < RETRY_MAX:
            await self.ADapi.run_in(self._retry_sync, RETRY_SECONDS, tries = tries + 1)

    def _retry_sync(self, **kwargs) -> None:
        self.ADapi.create_task(self._sync(kwargs['tries']))

    async def _updateDNS(self) -> bool:
        """ Changes only the content (and the proxy setting if enable_proxy is set). TTL and comment stay. """

        payload:dict = {"content": self.public_ip}
        if self.proxy is not None:
            payload["proxied"] = self.proxy
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.patch(self.reqUrl, headers=self.headersList, json=payload) as response:
                    body = await response.text()
                    if 200 <= response.status < 300 and json.loads(body).get('success', True):
                        self.ADapi.log(
                            f"{self.name}: {self.record_name} changed from {self.cloudflare_ip} to {self.public_ip} in Cloudflare.",
                            level='INFO'
                        )
                        self.cloudflare_ip = self.public_ip
                        return True
                    self.ADapi.log(
                        f"{self.name}: Not able to update {self.record_name} in Cloudflare. Status: {response.status}. {body[:200]}",
                        level='WARNING'
                    )
        except Exception as e:
            self.ADapi.log(f"{self.name}: Not able to update {self.record_name} in Cloudflare. Exception: {e}", level='WARNING')
        return False
