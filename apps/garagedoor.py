""" GarageDoor
Opening and closing of a cover entity

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon import adbase as ad
import json
from datetime import datetime
import os
from utils_apps import save_image_with_timestamp

AWAY_TRANSLATE:str = 'away'
NIGHT_TRANSLATE:str = 'night'

class GarageDoor(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.target_directory = self.args.get('target_directory', 'www/snapshots/') # '/root/.homeassistant/www/snapshots/'
        self.local_directory = self.args.get('local_directory', '/local/snapshots/')

        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        self.notify_receiver = self.args['notify_receiver']

        self.event_listen_str:str = 'MODE_CHANGE'
        language = self.args.get('lightwand_language', 'en')
        language_file = self.args.get('language_file', '/conf/apps/Lightwand/translations.json')
        try:
            with open(language_file) as lang:
                translations = json.load(lang)
        except FileNotFoundError:
            self.ADapi.log("Translation file not found", level = 'DEBUG')
        else:
            self.event_listen_str = translations[language]['MODE_CHANGE']
            global AWAY_TRANSLATE
            AWAY_TRANSLATE = translations[language]['away']
            global NIGHT_TRANSLATE
            NIGHT_TRANSLATE = translations[language]['night']

        self.garage = self.args['garage']

        if 'ios_open' in self.args:
            ios_open = self.args['ios_open']
            self.ADapi.listen_event(self._ios_open_garage, "ios.action_fired",
                                    actionName = ios_open,
                                    namespace = self.HASS_namespace
            )
        if 'ios_close' in self.args:
            ios_close = self.args['ios_close']
            self.ADapi.listen_event(self._ios_close_garage, "ios.action_fired",
                                    actionName = ios_close,
                                    namespace = self.HASS_namespace
            )
        auto_open_setup:dict = self.args.get('auto_open', {})
        for item in auto_open_setup:
            item.update({'handler' : None})
            if 'switch' in item:
                self.ADapi.listen_state(self._autoOpenGarage, item['switch'],
                                        item = item,
                                        namespace = self.HASS_namespace
                )
                if self.ADapi.get_state(item['switch'], namespace = self.HASS_namespace) == 'on':
                    self._start_listen_to_auto_open_garagedoor(item = item,
                                                               namespace = self.HASS_namespace)
            else:
                self._start_listen_to_auto_open_garagedoor(item = item,
                                                           namespace = self.HASS_namespace)

        self.close_garagedoor_action:str = 'close_garagedoor_' + str(self.garage)
        self.camera = self.args.get('camera', None)
        self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action", namespace = self.HASS_namespace)

        # Listens for mode events
        self.ADapi.listen_event(self.mode_event, self.event_listen_str, namespace = self.HASS_namespace)

    def mode_event(self, event_name, data, **kwargs) -> None:
        """ Listens to mode events and reacts on night and away.
        """
        if data['mode'] in (AWAY_TRANSLATE, NIGHT_TRANSLATE):
            if self.ADapi.get_state(self.garage, namespace = self.namespace) != 'closed':
                self.send_photo_notification()

    def send_photo_notification(self):
        data = {
            'tag' : str(self.garage),
            'actions' : [{ 'action' : self.close_garagedoor_action, 'title' : 'Close' }]
            }
        if self.camera is not None:
            local_path = save_image_with_timestamp(
                                                    ADapi = self.ADapi,
                                                    target_directory=self.target_directory,
                                                    local_directory=self.local_directory,
                                                    camera_entity=self.camera,
                                                    namespace=self.HASS_namespace,
            )
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
        self.ADapi.call_service('cover/open_cover',
                                entity_id = self.garage,
                                namespace = self.HASS_namespace)

    def _ios_close_garage(self, event_name, data, **kwargs) -> None:
        self.close_garage_door()

    def close_garage_door(self):
        self.ADapi.call_service('cover/close_cover',
                                entity_id = self.garage,
                                namespace = self.HASS_namespace)

    def _autoOpenGarage(self, entity, attribute, old, new, kwargs) -> None:
        item = kwargs['item']
        if new == 'on':
            self._start_listen_to_auto_open_garagedoor(item = item)

        else:
            self._stop_listen_handler(item = item)

    def _start_listen_to_auto_open_garagedoor(self, item:dict) -> None:
        item['handler'] = self.ADapi.listen_state(
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
                self.ADapi.call_service('input_boolean/turn_off',
                    entity_id = item['switch'],
                    namespace = self.HASS_namespace
                )
            self._stop_listen_handler(item = item)

    def _stop_listen_handler(self, item:dict):
        if item['handler'] is not None:
            try:
                self.ADapi.cancel_listen_state(item['handler'])
            except:
                self.ADapi.log(
                    f"Not possible to stop listen state for {item['handler']} in Garagedoor",
                    level = 'DEBUG'
                )
            item.update({'handler' : None})

    def _notify_event(self, event_name, data, **kwargs) -> None:
        if data['action'] == self.close_garagedoor_action:
            self.close_garage_door()
