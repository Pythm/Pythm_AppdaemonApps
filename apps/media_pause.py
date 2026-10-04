""" Pause Media
Pause media playing on device based on sensor input

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

class MediaPause(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.SensorHandler:list = []
        # Players this app has paused, and when. Only those are resumed.
        self.paused_by_app:dict = {}

        self.sensors = _as_list(self.args.get('sensors', []))
        self.mediaplayer = _as_list(self.args['media_player'])
        # Seconds all sensors have to be off before the players are paused
        pause_delay = int(self.args.get('pause_delay', 60))
        # A pause older than this many seconds is not resumed when a sensor turns on
        self.resume_within = int(self.args.get('resume_within', 14400))

        for sensor in self.sensors:
            self.ADapi.listen_state(self.StopMediaPlaying, sensor,
                new = 'off',
                duration = pause_delay,
                namespace = self.HASS_namespace
            )

    def StopMediaPlaying(self, entity, attribute, old, new, kwargs) -> None:
        """ Pauses the media players when all sensors have been off for the delay """

        for sensor in self.sensors:
            if self.ADapi.get_state(sensor, namespace = self.HASS_namespace) == 'on':
                return

        now = self.ADapi.get_now()
        for player in self.mediaplayer:
            state = self.ADapi.get_state(player, namespace = self.HASS_namespace)

            if state not in {None, 'off', 'standby', 'unavailable', 'unknown', 'idle', 'paused'}:
                self.ADapi.call_service('media_player/media_pause',
                    entity_id = player,
                    namespace = self.HASS_namespace
                )
                self.paused_by_app[player] = now

        if self.paused_by_app and not self.SensorHandler:
            for sensor in self.sensors:
                handler = self.ADapi.listen_state(self.StartMediaPlaying, sensor,
                    new = 'on',
                    namespace = self.HASS_namespace
                )
                self.SensorHandler.append(handler)

    def StartMediaPlaying(self, entity, attribute, old, new, kwargs) -> None:
        """ Resumes the players this app paused, when a sensor turns on """

        now = self.ADapi.get_now()
        for player, paused_at in self.paused_by_app.items():
            if (
                (now - paused_at).total_seconds() <= self.resume_within
                and self.ADapi.get_state(player, namespace = self.HASS_namespace) == 'paused'
            ):
                self.ADapi.call_service('media_player/media_play',
                    entity_id = player,
                    namespace = self.HASS_namespace
                )
        self.paused_by_app = {}

        for handler in self.SensorHandler:
            self.ADapi.cancel_listen_state(handler, silent = True)
        self.SensorHandler = []
