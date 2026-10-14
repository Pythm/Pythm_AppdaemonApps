""" Keep a rechargeable device (for example an iPad) from sitting at full charge

    Turns the charger switch off at max_level and on again at min_level.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon import adbase as ad

class MobileChargerController(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.charger_switch = self.args['charger_switch']
        self.battery_state = self.args['battery_state']
        self.battery_level = self.args['battery_level']
        self.location = self.args.get('device_location')

        self.max_level:float = float(self.args.get('max_level', 80))
        self.min_level:float = float(self.args.get('min_level', 75))
        check_interval:int = int(self.args.get('check_interval', 900))

        for entity in (self.charger_switch, self.battery_state, self.battery_level):
            if self.ADapi.get_state(entity, namespace = self.HASS_namespace) is None:
                self.ADapi.log(f"{self.name}: {entity} was not found.", level = 'WARNING')

        # React when the sensors update, and check regularly in case they do not.
        self.ADapi.listen_state(self._sensor_changed, [self.battery_level, self.battery_state],
            namespace = self.HASS_namespace
        )
        self.ADapi.run_every(self.check_battery_state, "now+180", check_interval)

    def _sensor_changed(self, entity, attribute, old, new, kwargs) -> None:
        self.check_battery_state()

    def check_battery_state(self, **kwargs):
        try:
            battery_level = float(self.ADapi.get_state(self.battery_level, namespace = self.HASS_namespace))
        except (TypeError, ValueError):
            return
        # The Companion app reports 'Not Charging' on iOS and 'not_charging' on Android
        battery_state = str(self.ADapi.get_state(self.battery_state, namespace = self.HASS_namespace)).lower().replace('_', ' ')
        switch = self.ADapi.get_state(self.charger_switch, namespace = self.HASS_namespace)

        if battery_state in ('charging', 'full') and battery_level >= self.max_level:
            if (
                switch != 'off'
                and (self.location is None or self.ADapi.get_state(self.location, namespace = self.HASS_namespace) == 'home')
            ):
                self.ADapi.call_service('homeassistant/turn_off',
                    entity_id = self.charger_switch,
                    namespace = self.HASS_namespace
                )
        elif battery_state == 'not charging' and switch == 'off' and battery_level <= self.min_level:
            self.ADapi.call_service('homeassistant/turn_on',
                entity_id = self.charger_switch,
                namespace = self.HASS_namespace
            )
