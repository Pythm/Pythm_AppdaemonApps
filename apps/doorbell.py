""" Doorbell
    Notifications to phone and media players on Doorbell

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
        self.notify_reciever = self.args['notify_reciever']
        self.notify_message = self.args.get('notify_message', 'Someone at the door')
        self.notify_when_away = self.args.get('notify_when_away', True)

        doorbell = self.args['doorbell']
        self.listen_state(self.doorRing, doorbell, new = 'on')

        self.camera = self.args.get('camera', None)
        self.media_player = self.args.get('media_player', [])

    def doorRing(self, entity, attribute, old, new, kwargs) -> None:
        """ Sends snapshot from video device on doorbell ring to mobile devices.
        """
        if self.camera is not None:
            local_path = self.save_image_with_timestamp()
            data = {
                'tag' : str(self.name),
                'image' : local_path
                }
            self.playStreamOnMediaPlayers()
        else:
            data = {'tag' : str(self.name)}

        self.notify_app.send_notification(
            message = f"Besøk",
            message_recipient = self.notify_reciever,
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
                    entity_id = self.camera
                )

    def save_image_with_timestamp(self):
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
            entity_id = self.camera
        )

        return local_path

