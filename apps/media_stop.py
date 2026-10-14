""" Stop Media
Stop media playing on device based on sensor input

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon import adbase as ad

def _as_list(value) -> list:
    """ A single entity in the configuration is treated as a list of one. """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)

class MediaStop(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.SensorHandler:list = []

        self.sensors = _as_list(self.args.get('sensors', []))
        self.mediaplayer = _as_list(self.args['media_player'])

        if 'activate_switch' in self.args:
            self.activate_switch = self.args['activate_switch']
            # Both on and off, so the sensors are only listened to while the switch is on
            self.ADapi.listen_state(self.autoTurnOff, self.activate_switch,
                namespace = self.HASS_namespace
            )
            if self.ADapi.get_state(self.activate_switch, namespace = self.HASS_namespace) == 'on':
                self._listen_to_sensors()
        else:
            self._listen_to_sensors()

    def _listen_to_sensors(self) -> None:
        self._stop_listening_to_sensors()
        for sensor in self.sensors:
            handler = self.ADapi.listen_state(self.StopMediaPlaying, sensor,
                new = 'on',
                namespace = self.HASS_namespace
            )
            self.SensorHandler.append(handler)

    def _stop_listening_to_sensors(self) -> None:
        for handler in self.SensorHandler:
            self.ADapi.cancel_listen_state(handler, silent = True)
        self.SensorHandler = []

    def autoTurnOff(self, entity, attribute, old, new, kwargs) -> None:
        """ Starts listening for sensors to turn off media while the switch is on """

        if new == 'on':
            self._listen_to_sensors()
        elif new == 'off':
            self._stop_listening_to_sensors()

    def StopMediaPlaying(self, entity, attribute, old, new, kwargs) -> None:
        """ Auto stops mediaplayer on sensor detection/activation """

        for player in self.mediaplayer:
            state = self.ADapi.get_state(player, namespace = self.HASS_namespace)
            
            if state not in {None, 'off', 'standby', 'unavailable', 'unknown', 'idle'}:
                self.ADapi.call_service('media_player/media_stop',
                    entity_id = player,
                    namespace = self.HASS_namespace
                )
