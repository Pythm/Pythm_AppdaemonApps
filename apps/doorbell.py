""" Doorbell
    Notifications to phone and media players on Doorbell activity

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.1"

from appdaemon import adbase as ad
from datetime import datetime
from utils_apps import save_image_with_timestamp

class Doorbell(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.target_directory = self.args.get('target_directory', 'www/snapshots/') # '/root/.homeassistant/www/snapshots/'
        self.local_directory = self.args.get('local_directory', '/local/snapshots/')

        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        self.notify_receiver = self.args['notify_receiver']
        self.notify_message = self.args.get('notify_message', 'Someone at the door')
        self.notify_when_away = self.args.get('notify_when_away', True)

        doorbell = self.args['doorbell']
        self.ADapi.listen_state(self._doorRing, doorbell,
                                new = 'on',
                                namespace = self.HASS_namespace)
        
        if 'chime' in self.args:
            self.chime = self.args['chime']
            self.daytime_volume = self.args.get('daytime_volume', 80)
            daytime_start = self.args.get('daytime_start', '06:00:00')
            self.nighttime_volume = self.args.get('nighttime_volume', 30)
            daytime_stop = self.args.get('daytime_stop', '22:00:00')

            self.ADapi.run_daily(self.set_day_volume, daytime_start)
            self.ADapi.run_daily(self.set_night_volume, daytime_stop)
            if self.ADapi.now_is_between(daytime_start, daytime_stop):
                self.set_day_volume()
            else:
                self.set_night_volume()

        self.camera = self.args.get('camera', None)
        self.media_player = self.args.get('media_player', [])

    def _doorRing(self, entity, attribute, old, new, kwargs) -> None:
        """ Sends snapshot from video device on doorbell ring to mobile devices.
        """
        if self.camera is not None:
            local_path = save_image_with_timestamp(
                                                  ADapi = self.ADapi,
                                                  target_directory=self.target_directory,
                                                  local_directory=self.local_directory,
                                                  camera_entity=self.camera,
                                                  namespace=self.HASS_namespace,
            )
            data = {
                'tag' : str(self.ADapi.name),
                'image' : local_path
                }
            self.playStreamOnMediaPlayers()
        else:
            data = {'tag' : str(self.ADapi.name)}

        self.notify_app.send_notification(
            message = self.notify_message,
            message_recipient = self.notify_receiver,
            also_if_not_home = self.notify_when_away,
            data = data
        )

    def playStreamOnMediaPlayers(self):
        """ Plays stream form video device to media players
        """
        for player in self.media_player:
            state = self.ADapi.get_state(player, namespace = self.HASS_namespace)
            if state not in {'off', 'standby'}:
                self.ADapi.call_service(
                    'camera/play_stream',
                    media_player = player,
                    entity_id = self.camera,
                    namespace = self.HASS_namespace
                )

    def set_day_volume(self, kwargs=None):
        self.ADapi.call_service('number/set_value',
            value = self.daytime_volume,
            entity_id = self.chime,
            namespace = self.HASS_namespace
        )

    def set_night_volume(self, kwargs=None):
        self.ADapi.call_service('number/set_value',
            value = self.nighttime_volume,
            entity_id = self.chime,
            namespace = self.HASS_namespace
        )