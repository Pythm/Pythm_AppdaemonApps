""" Stop Media 
Pause media playing on device based on sensor input

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

from appdaemon.plugins.hass.hassapi import Hass

class MediaPause(Hass):

    def initialize(self):
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.SensorHandler:list = []

        self.sensors = self.args.get('sensors', [])
        self.mediaplayer = self.args['media_player']

        for sensor in self.sensors:
            self.listen_state(self.StopMediaPlaying, sensor,
                new = 'off',
                duration = 60,
                namespace = self.HASS_namespace
            )

    def StopMediaPlaying(self, entity, attribute, old, new, kwargs) -> None:
        """ Auto stops mediaplayer on sensor detection/activation
        """
        for sensor in self.sensors:
            if self.get_state(sensor, namespace = self.HASS_namespace) == 'on':
                break

        for player in self.mediaplayer:
            state = self.get_state(player, namespace = self.HASS_namespace)
            
            if state not in {'off', 'standby', 'unavailable', 'idle', 'paused'}:
                self.call_service('media_player/media_pause',
                    entity_id = player,
                    namespace = self.HASS_namespace
                )

                if not self.SensorHandler:
                    for sensor in self.sensors:
                        handler = self.listen_state(self.StartMediaPlaying, sensor,
                            new = 'on',
                            namespace = self.HASS_namespace
                        )
                        self.SensorHandler.append(handler)


    def StartMediaPlaying(self, entity, attribute, old, new, kwargs) -> None:
        """ Auto starts mediaplayer on sensor detection/activation
        """
        for player in self.mediaplayer:
            state = self.get_state(player, namespace = self.HASS_namespace)
            
            if state == 'paused':
                self.call_service('media_player/media_play',
                    entity_id = player,
                    namespace = self.HASS_namespace
                )

        for handler in self.SensorHandler:
            try:
                self.cancel_listen_state(handler)
                handler = None
            except:
                self.log(
                    f"Ikke mulig å stoppe listen state for {handler} i PauseMedia",
                    level = 'DEBUG'
                )
        self.SensorHandler = []