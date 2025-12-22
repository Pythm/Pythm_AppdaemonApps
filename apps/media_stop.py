""" Stop Media 
Stop media playing on device based on sensor input

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

from appdaemon.plugins.hass.hassapi import Hass

class MediaStop(Hass):

    def initialize(self):
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.SensorHandler:list = []

        self.sensors = self.args.get('sensors', [])
        self.mediaplayer = self.args['media_player']

        if 'activate_switch' in self.args:
            self.activate_switch = self.args['activate_switch']
            self.listen_state(self.autoTurnOff, self.activate_switch,
                new = 'on',
                namespace = self.HASS_namespace
            )
        else:
            for sensor in self.sensors:
                handler = self.listen_state(self.StopMediaPlaying, sensor,
                    new = 'on',
                    namespace = self.HASS_namespace
                )

    def autoTurnOff(self, entity, attribute, old, new, kwargs) -> None:
        """ Starts listening for sensors to turn off media """

        if new == 'on':
            for sensor in self.sensors:
                handler = self.listen_state(self.StopMediaPlaying, sensor,
                    new = 'on',
                    namespace = self.HASS_namespace
                )
                self.SensorHandler.append(handler)
        else:
            for handler in self.SensorHandler:
                try:
                    self.cancel_listen_state(handler)
                    handler = None
                except:
                    self.log(
                        f"Ikke mulig å stoppe listen state for {handler} i StopMedia",
                        level = 'DEBUG'
                    )
            self.SensorHandler = []

    def StopMediaPlaying(self, entity, attribute, old, new, kwargs) -> None:
        """ Auto stops mediaplayer on sensor detection/activation """

        for player in self.mediaplayer:
            state = self.get_state(player, namespace = self.HASS_namespace)
            
            if state not in {'off', 'standby', 'unavailable', 'idle'}:
                self.call_service('media_player/media_stop',
                    entity_id = player,
                    namespace = self.HASS_namespace
                )
