""" Update Cloudflare DNS with new ip

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

import asyncio
import json
import datetime

from appdaemon import adbase as ad
import aiohttp


class Change_DNS(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()

        self.public_ip:str = None
        self.dns_ip:str = None
        self.record_name:str = None
        self.proxy:bool = self.args.get('enable_proxy', True)

        self.cloudflare_api_token = self.args['cloudflare_api_token']
        self.zone_id = self.args['zone_id']
        self.dns_record_id = self.args['dns_record_id']

        self.headersList = {
          "Accept": "*/*",
          "Authorization": "Bearer " + str(self.cloudflare_api_token)
          }
        self.reqUrl = "https://api.cloudflare.com/client/v4/zones/" + str(self.zone_id) + "/dns_records/" + str(self.dns_record_id)

        if 'ip_sensor' in self.args:
            ip_sensor = self.args['ip_sensor']
            self.ADapi.listen_state(self._ha_DNS_ip_sensor_changed, ip_sensor)
            self.public_ip = self.ADapi.get_state(ip_sensor)
        else:
            self.ADapi.create_task(self._get_public_ip())
            self.ADapi.run_hourly(self._checkPublicIPAddress, "00:10:00")

        self.ADapi.create_task(self._get_current_DNS())

    def _ha_DNS_ip_sensor_changed(self, entity, attribute, old, new, kwargs) -> None:
        if (
            new != 'unavailable'
            and new != 'unknown'
            and new != self.public_ip
        ):
            self.public_ip = new
            self.ADapi.log(f"Detected new IP: {self.public_ip}") ###
            self.ADapi.create_task(self._updateDNS())

    def _checkPublicIPAddress(self, kwargs) -> None:
        self.ADapi.create_task(self._get_public_ip())

    async def _get_public_ip(self) -> None:
        try :
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.ipify.org") as response:
                    if response.status == 200:
                        result = await response.text()
                    else:
                        self.ADapi.log(f"Error {response.status}: {await response.text()}")

                    if 200 <= response.status < 300:
                        result = await response.text()
                        api_result_str:str = result
                        
                    else:
                        self.ADapi.log(
                            f"Not able to get IP from ipify. Request returned with status: {response.status}. "
                            f"Exception: {e}",
                            level='INFO'
                        )
                        api_result_str = None
        except Exception as e:
            self.ADapi.log(
                f"Not able to get IP from ipify. "
                f"Exception: {e}",
                level='INFO'
            )
            api_result_str = None

        if api_result_str is not None:
            self.public_ip = api_result_str
            if (
                api_result_str != self.dns_ip
                and self.dns_ip is not None
            ):
                self.ADapi.log(
                    f"Public IP address changed to {self.public_ip}. Updating cloudflare."
                ) ###
                self.ADapi.create_task(self._updateDNS())

    async def _get_current_DNS(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.reqUrl, headers=self.headersList) as response:
                    if 200 <= response.status < 300:
                        api_result_str = await response.text()
                        api_result_dict = json.loads(api_result_str)
                        cloudflare_ip = api_result_dict['result']['content']
                        self.record_name = api_result_dict['result']['name']
                    else:
                        self.ADapi.log(
                            f"Not able to get IP from cloudflare. Request returned with status: {response.status}. "
                            "Exception was not provided.",
                            level='INFO'
                        )
                        cloudflare_ip = None
        except Exception as e:
            self.ADapi.log(f"Not able to get IP from cloudflare. "
                f"Exception: {e}",
                level='INFO')
            cloudflare_ip = None

        if cloudflare_ip is not None:
            self.dns_ip = cloudflare_ip
            if (
                cloudflare_ip != self.public_ip
                and self.public_ip is not None
            ):
                self.ADapi.create_task(self._updateDNS())

    async def _updateDNS(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                payload = json.dumps({
                    "type": "A",
                    "name": self.record_name,
                    "content": self.public_ip,
                    "proxied": self.proxy
                })
                async with session.put(self.reqUrl, headers=self.headersList, data=payload) as response:
                    if 200 <= response.status < 300:
                        api_result_str = await response.text()
                        api_result_dict = json.loads(api_result_str)
                        self.ADapi.log(f"Result from API call to update IP address: {api_result_dict['result']}") ###
                    else:
                        self.ADapi.log(
                            f"Not able to update IP to cloudflare. Request returned with status: {response.status}. "
                            "Exception was not provided.",
                            level='INFO'
                        )
        except Exception as e:
            self.ADapi.log(f"Not able to update IP to cloudflare. "
                f"Exception: {e}",
                level='INFO')