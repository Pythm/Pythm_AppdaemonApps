""" FireAlarm
Trigger a mode change if fire alarm is triggered.
Turns off switches and opens screens/garagedoors

    @Pythm / https://github.com/Pythm

"""

__version__ = "0.1.2"

from appdaemon.plugins.hass.hassapi import Hass
import json
import csv

# Translations from json for 'MODE_CHANGE' events
FIRE_TRANSLATE:str = 'fire'
FALSE_ALARM_TRANSLATE:str = 'false-alarm'

class FireAlarm(Hass):

    def initialize(self):
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
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
            global FIRE_TRANSLATE
            FIRE_TRANSLATE = translations[language]['fire']
            global FALSE_ALARM_TRANSLATE
            FALSE_ALARM_TRANSLATE = translations[language]['false-alarm']

        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.get_app(name_of_notify_app)
        self.notify_receiver = self.args['notify_receiver']

        self.anyone_home = True
        mode_management_app_name = self.args.get('modeManagementApp', None)
        if mode_management_app_name is None:
            self.mode_management_app = None
        else:
            self.mode_management_app = self.get_app(mode_management_app_name)
            self.anyone_home = self.mode_management_app.anyone_home()
        

        alarms = self.args.get('alarms', [])
        for alarm in alarms:
            self.listen_state(self._alarmactivated, alarm)
        
        self.turn_off_items = self.args.get('turn_off', [])

        sensor_states = self.get_state()
        for sensor_id, sensor_states in sensor_states.items():
            if 'media_player.' in sensor_id:
                if not sensor_id in self.turn_off_items:
                    self.turn_off_items.append(sensor_id)

        self.screens = self.args.get('screens', [])

    def _alarmactivated(self, entity, attribute, old, new, kwargs) -> None:
        if new == 'on':
            self.fire_event(self.event_listen_str, mode = FIRE_TRANSLATE)
            for item in self.turn_off_items:
                try:
                    if self.get_state(item) == 'on':
                        self.turn_off(item)
                except Exception as exc:
                    self.log(
                        f"Could not turn off {item} when fire alarm was trigered. Exception: {exc}",
                        level = 'INFO'
                    )

            if self.mode_management_app:
                self.anyone_home = self.mode_management_app.anyone_home()
            if self.anyone_home:
                for screen in self.screens:
                    try:
                        if self.get_state(screen, attribute='current_position') != 100:
                            self.call_service('cover/open_cover', entity_id= screen)
                    except Exception as exc:
                        self.log(
                            f"Could not open {screen} when fire alarm was trigered. Exception: {exc}",
                            level = 'INFO'
                        )

            self.notify_app.send_notification(
                message = f"at {entity}",
                message_title = "Smoke detected",
                message_recipient = self.notify_receiver,
                also_if_not_home = True
            )

        elif (
            new == 'off'
            and old == 'on'
        ):
            self.fire_event(self.event_listen_str, mode = FALSE_ALARM_TRANSLATE)
        elif (
            new not in ['unavailable', 'unknown']
        ):
            self.log(
                f"Fire Alarm: {entity}. New: {new}. Old: {old}. Logic not implemented. Please open a issue with this info.",
                level = 'INFO'
            )