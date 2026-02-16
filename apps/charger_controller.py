""" Turn off charging when above 80%


    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

from appdaemon import adbase as ad
from datetime import timedelta

class MobileChargerController(ad.ADBase):
    
    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.charger_switch = self.args['charger_switch']
        self.battery_state = self.args['battery_state']
        self.battery_level = self.args['battery_level']
        self.location = self.args.get('device_location')

        now = self.ADapi.datetime()
        runtime = now.replace(second=50, microsecond=0)
        runtime += timedelta(minutes=3)
        self.ADapi.run_every(self.check_battery_state, runtime, 900)


    def check_battery_state(self, **kwargs):
        battery_state = self.ADapi.get_state(self.battery_state, namespace = self.HASS_namespace)
        switch = self.ADapi.get_state(self.charger_switch, namespace = self.HASS_namespace)
        battery_level = float(self.ADapi.get_state(self.battery_level, namespace = self.HASS_namespace))
        if battery_state in ('Charging', 'Full') and battery_level >= 80:
            if self.location is None or self.ADapi.get_state(self.location, namespace = self.HASS_namespace) == 'home':
                self.ADapi.call_service('switch/turn_off',
                    entity_id = self.charger_switch,
                    namespace = self.HASS_namespace
                )
        elif battery_state == 'Not Charging' and switch == 'off' and battery_level <= 75:
            self.ADapi.call_service('switch/turn_on',
                entity_id = self.charger_switch,
                namespace = self.HASS_namespace
            )
