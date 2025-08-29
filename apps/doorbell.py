""" Doorbell
    Notifications to phone and media players on Doorbell activity

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

from appdaemon.plugins.hass.hassapi import Hass
import os
from datetime import datetime

class Doorbell(Hass):

    def initialize(self):
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')

        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.get_app(name_of_notify_app)
        self.notify_receiver = self.args['notify_receiver']
        self.notify_message = self.args.get('notify_message', 'Someone at the door')
        self.notify_when_away = self.args.get('notify_when_away', True)

        doorbell = self.args['doorbell']
        self.listen_state(self._doorRing, doorbell,
                          new = 'on',
                          namespace = self.HASS_namespace)

        self.camera = self.args.get('camera', None)
        self.media_player = self.args.get('media_player', [])

    def _doorRing(self, entity, attribute, old, new, kwargs) -> None:
        """ Sends snapshot from video device on doorbell ring to mobile devices.
        """
        if self.camera is not None:
            local_path = self._save_image_with_timestamp()
            data = {
                'tag' : str(self.name),
                'image' : local_path
                }
            self.playStreamOnMediaPlayers()
        else:
            data = {'tag' : str(self.name)}

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
            state = self.get_state(player, namespace = self.HASS_namespace)
            if state not in {'off', 'standby'}:
                self.call_service(
                    'camera/play_stream',
                    media_player = player,
                    entity_id = self.camera,
                    namespace = self.HASS_namespace
                )

    def _save_image_with_timestamp(self):
        """ Saves image from camera to file and returns path as local path
        """
        target_directory = '/root/.homeassistant/www/doorbell/'
        local_directory = '/local/doorbell/'
        # Ensure the target directory exists
        if not os.path.exists(target_directory):
            os.makedirs(target_directory)

        now = datetime.now()
        formatted_date = now.strftime("%Y%m%d_%H%M%S")
        file_extension = 'jpg'
        target_filename = f"doorbell_{formatted_date}.{file_extension}"
        
        # Construct full path to the new file
        target_path = os.path.join(target_directory, target_filename)
        local_path = os.path.join(local_directory, target_filename)

        self.call_service(
            'camera/snapshot',
            filename = target_path,
            entity_id = self.camera,
            namespace = self.HASS_namespace
        )
        return local_path