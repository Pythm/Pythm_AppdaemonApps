""" GarageDoor
Opening and closing of a cover entity

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon.plugins.hass.hassapi import Hass
import json
from datetime import datetime
import os

AWAY_TRANSLATE:str = 'away'
NIGHT_TRANSLATE:str = 'night'

class GarageDoor(Hass):

    def initialize(self):
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.get_app(name_of_notify_app)
        self.notify_receiver = self.args['notify_receiver']

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.event_listen_str:str = 'MODE_CHANGE'
        language = self.args.get('lightwand_language', 'en')
        language_file = self.args.get('language_file', '/conf/apps/Lightwand/translations.json')
        try:
            with open(language_file) as lang:
                translations = json.load(lang)
        except FileNotFoundError:
            self.log("Translation file not found", level = 'DEBUG')
        else:
            self.event_listen_str = translations[language]['MODE_CHANGE']
            global AWAY_TRANSLATE
            AWAY_TRANSLATE = translations[language]['away']
            global NIGHT_TRANSLATE
            NIGHT_TRANSLATE = translations[language]['night']

        self.garage = self.args['garage']

        if 'ios_open' in self.args:
            ios_open = self.args['ios_open']
            self.listen_event(self._ios_open_garage, "ios.action_fired",
                              actionName = ios_open,
                              namespace = self.HASS_namespace
            )
        if 'ios_close' in self.args:
            ios_close = self.args['ios_close']
            self.listen_event(self._ios_close_garage, "ios.action_fired",
                              actionName = ios_close,
                              namespace = self.HASS_namespace
            )
        auto_open_setup:dict = self.args.get('auto_open', {})
        for item in auto_open_setup:
            item.update({'handler' : None})
            if 'switch' in item:
                self.listen_state(self._autoOpenGarage, item['switch'],
                                  item = item,
                                  namespace = self.HASS_namespace
                )
                if self.get_state(item['switch'], namespace = self.HASS_namespace) == 'on':
                    self._start_listen_to_auto_open_garagedoor(item = item,
                                                               namespace = self.HASS_namespace)
            else:
                self._start_listen_to_auto_open_garagedoor(item = item,
                                                           namespace = self.HASS_namespace)

        self.close_garagedoor_action:str = 'close_garagedoor_' + str(self.garage)
        self.camera = self.args.get('camera', None)
        self.listen_event(self._notify_event, "mobile_app_notification_action", namespace = self.HASS_namespace)

        # Listens for mode events
        self.listen_event(self.mode_event, self.event_listen_str, namespace = self.HASS_namespace)

    def mode_event(self, event_name, data, **kwargs) -> None:
        """ Listens to mode events and reacts on night and away.
        """
        if data['mode'] in (AWAY_TRANSLATE, NIGHT_TRANSLATE):
            if self.get_state(self.garage,
                              namespace = self.namespace) != 'closed':
                data = {
                    'tag' : str(self.garage),
                    'actions' : [{ 'action' : self.close_garagedoor_action, 'title' : 'Close' }]
                    }
                if self.camera is not None:
                    local_path = self._save_image_with_timestamp()
                    data.update({ 'image' : local_path })

                self.notify_app.send_notification(
                    message = "Close the garage?",
                    message_title = "Garage still open",
                    message_recipient = self.notify_receiver,
                    also_if_not_home = True,
                    data = data
                )

    def _ios_open_garage(self, event_name, data, **kwargs) -> None:
        self.open_garage_door()

    def open_garage_door(self):
        self.call_service('cover/open_cover',
                          entity_id = self.garage,
                          namespace = self.HASS_namespace)

    def _ios_close_garage(self, event_name, data, **kwargs) -> None:
        self.close_garage_door()

    def close_garage_door(self):
        self.call_service('cover/close_cover',
                          entity_id = self.garage,
                          namespace = self.HASS_namespace)

    def _autoOpenGarage(self, entity, attribute, old, new, kwargs) -> None:
        item = kwargs['item']
        if new == 'on':
            self._start_listen_to_auto_open_garagedoor(item = item)

        else:
            self._stop_listen_handler(item = item)

    def _start_listen_to_auto_open_garagedoor(self, item:dict) -> None:
        item['handler'] = self.listen_state(
            self._returningHome,
            item['presence'],
            new = 'home',
            item = item,
            namespace = self.HASS_namespace
        )

    def _returningHome(self, entity, attribute, old, new, kwargs) -> None:
        item = kwargs['item']
        if old != 'unavailable':
            self.open_garage_door()
            if 'switch' in item:
                self.call_service('input_boolean/turn_off',
                    entity_id = item['switch'],
                    namespace = self.HASS_namespace
                )
            self._stop_listen_handler(item = item)

    def _stop_listen_handler(self, item:dict):
        if item['handler'] is not None:
            try:
                self.cancel_listen_state(item['handler'])
            except:
                self.log(
                    f"Not possible to stop listen state for {item['handler']} in Garagedoor",
                    level = 'DEBUG'
                )
            item.update({'handler' : None})

    def _notify_event(self, event_name, data, **kwargs) -> None:
        if data['action'] == self.close_garagedoor_action:
            self.close_garage_door()


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