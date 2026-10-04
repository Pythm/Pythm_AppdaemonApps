""" Doorbell
    Notifications to phone and media players on Doorbell activity

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon import adbase as ad
from utils_apps import save_image_with_timestamp, local_path_from_target

# A media player in one of these states is left alone
NO_STREAM_STATES = (None, 'off', 'standby', 'unavailable', 'unknown')

def _as_list(value) -> list:
    """ A single entity in the configuration is treated as a list of one. """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)

class Doorbell(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.target_directory = self.args.get('target_directory', 'www/snapshots/')
        self.snapshot_keep_days = self.args.get('snapshot_keep_days', None)
        try:
            self.local_directory = local_path_from_target(
                self.target_directory
            )
        except ValueError as exc:
            self.ADapi.log(f"{self.name}: {exc}", level="ERROR")
            raise

        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.notify_app is None:
            self.ADapi.log(f"{self.name}: Could not find app '{name_of_notify_app}'. Add it to 'dependencies'. Aborting setup", level = 'ERROR')
            return
        self.notify_receiver = self.args['notify_receiver']
        self.notify_title = self.args.get('notify_title', None)
        self.notify_message = self.args.get('notify_message', 'Someone at the door')
        self.notify_when_away = self.args.get('notify_when_away', True)

        self.camera = self.args.get('camera', None)
        self.media_player = _as_list(self.args.get('media_player', []))

        doorbell = self.args['doorbell']
        if str(doorbell).startswith('event.'):
            # An event entity has a timestamp as state, so every change is a ring
            self.ADapi.listen_state(self._doorRing, doorbell,
                                    namespace = self.HASS_namespace)
        else:
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

    def _doorRing(self, entity, attribute, old, new, kwargs) -> None:
        """ Sends snapshot from video device on doorbell ring to mobile devices """

        if new in (None, 'unavailable', 'unknown'):
            return

        data = {'tag' : str(self.ADapi.name)}
        if self.camera is not None:
            data['image'] = save_image_with_timestamp(
                                                  ADapi = self.ADapi,
                                                  target_directory=self.target_directory,
                                                  local_directory=self.local_directory,
                                                  camera_entity=self.camera,
                                                  namespace=self.HASS_namespace,
                                                  keep_days=self.snapshot_keep_days,
            )

        # The notification first, so a problem with a media player cannot stop it
        kwargs_notify = {}
        if self.notify_title is not None:
            kwargs_notify['message_title'] = self.notify_title
        self.notify_app.send_notification(
            message = self.notify_message,
            message_recipient = self.notify_receiver,
            also_if_not_home = self.notify_when_away,
            data = data,
            **kwargs_notify
        )

        if self.camera is not None:
            self.playStreamOnMediaPlayers()

    def playStreamOnMediaPlayers(self):
        """ Plays stream form video device to media players """

        for player in self.media_player:
            try:
                state = self.ADapi.get_state(player, namespace = self.HASS_namespace)
                if state in NO_STREAM_STATES:
                    continue
                if state == 'playing':
                    self.ADapi.call_service('media_player/media_stop',
                        entity_id = player,
                        namespace = self.HASS_namespace
                    )
                self.ADapi.call_service(
                    'camera/play_stream',
                    media_player = player,
                    entity_id = self.camera,
                    namespace = self.HASS_namespace
                )
            except Exception as exc:
                self.ADapi.log(f"{self.name}: Could not play the stream on {player}: {exc}", level = 'WARNING')

    def _set_chime_volume(self, volume) -> None:
        # number/set_value for a number entity, input_number/set_value for an input_number
        domain = str(self.chime).split('.')[0]
        self.ADapi.call_service(f'{domain}/set_value',
            value = volume,
            entity_id = self.chime,
            namespace = self.HASS_namespace
        )

    def set_day_volume(self, **kwargs):
        self._set_chime_volume(self.daytime_volume)

    def set_night_volume(self, **kwargs):
        self._set_chime_volume(self.nighttime_volume)
