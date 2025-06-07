""" Play music and turn on lights to wake up.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.1.0"

from appdaemon.plugins.hass.hassapi import Hass
import datetime
import json


class WakeUp(Hass):

    def initialize(self):

        # Namespaces for HASS and MQTT
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.MQTT_namespace:str = self.args.get('MQTT_namespace', 'default')
        self.mqtt = None

        self.music_handler = None
        self.light_run_handler = None
        if 'workday' in self.args:
            self.workday = self.args['workday']
        else:
            self.workday = 'binary_sensor.workday_sensor'
            if not self.entity_exists(self.get_entity(self.workday)):
                self.call_service("state/set",
                    entity_id = self.workday,
                    attributes = {'friendly_name' : 'Workday'},
                    state = 'on',
                    namespace = self.HASS_namespace
                )
                self.log(
                    "'workday' binary_sensor not defined in app configuration. Will fire morning mode every day. "
                    "https://www.home-assistant.io/integrations/workday/",
                    level = 'INFO'
                )

        if 'vacation' in self.args:
            self.away_state = self.args['vacation']
        else:
            self.away_state = 'input_boolean.vacation'
            if not self.entity_exists(self.get_entity(self.away_state)):
                self.call_service("state/set",
                    entity_id = self.away_state,
                    attributes = {'friendly_name' : 'Vacation'},
                    state = 'off',
                    namespace = self.HASS_namespace
                )
            else:
                self.log(
                    "'vacation' not configured. Using 'input_boolean.vacation' as default away state",
                    level = 'WARNING'
                )

        if 'alarm_switch' in self.args:
            self.alarm_switch = self.args['alarm_switch']
        else:
            self.alarm_switch = 'input_boolean.alarm_switch'
            if not self.entity_exists(self.get_entity(self.alarm_switch)):
                self.call_service("state/set",
                    entity_id = self.alarm_switch,
                    attributes = {'friendly_name' : 'Alarm switch'},
                    state = 'on',
                    namespace = self.HASS_namespace
                )

            else:
                self.log(
                    "'alarm_switch' not configured. Using 'input_boolean.alarm_switch' as default to play music every weekday",
                    level = 'INFO'
                )

        if 'alarm_switch_non_work_day' in self.args:
            self.alarm_switch_non_work_day = self.args['alarm_switch_non_work_day']
        else:
            self.alarm_switch_non_work_day = 'input_boolean.alarm_switch_non_work_day'
            if not self.entity_exists(self.get_entity(self.alarm_switch_non_work_day)):
                self.call_service("state/set",
                    entity_id = self.alarm_switch_non_work_day,
                    attributes = {'friendly_name' : 'Alarm switch Non work day'},
                    state = 'off',
                    namespace = self.HASS_namespace
                )

            elif 'workday' in self.args:
                self.log(
                    "'alarm_switch_non_work_day' not configured. Using 'input_boolean.alarm_switch_non_work_day' will not play music on weekends and holidays.",
                    level = 'INFO'
                )
            else:
                self.log(
                    "'alarm_switch_non_work_day' not configured. Using 'input_boolean.alarm_switch_non_work_day' will not play music on weekends",
                    level = 'INFO'
                )

        self.media_player = self.args['media_player']
        self.playlist = self.args['playlist']
        self.volume = self.args.get('volume', 0)

        self.wake_up_lights:list = self.args.get('wake_up_lights',[])
        self.wake_up_MQTTlights:list = self.args.get('wake_up_MQTTlights',[])
        if self.wake_up_MQTTlights:
            self.mqtt = self.get_plugin_api('MQTT')

        self.light_data:dict = self.args.get('light_data', {})
        self.light_data.update(
            {"state" : "ON"}
        )

        self.light_time_offset = self.args.get('light_time_offset',0)

        if 'time' in self.args: # Home Assistant input_datetime helper
            wake_up_time = self.args['time']
            self.listen_state(self.set_wake_up_time, wake_up_time,
                namespace = self.HASS_namespace,
                duration = 5
            )
            timestring =  self.get_state(wake_up_time,
                namespace = self.HASS_namespace
            )
            if timestring != '00:00:00':
                self.music_handler = self.run_daily(self.wake_up_music, timestring)
                if self.light_time_offset != 0:
                    timeToAdd = datetime.timedelta(minutes = self.light_time_offset)
                    newtime = self.parse_datetime(timestring) + timeToAdd
                    timestring = str(newtime.time())
                self.light_run_handler = self.run_daily(self.wake_up_with_lights, timestring)

        self.conditions:list = self.args.get('conditions',[])

    def set_wake_up_time(self, entity, attribute, old, new, kwargs):
        """ Sets new wake up time based on input
        """
        if self.music_handler is not None:
            if self.timer_running(self.music_handler):
                try:
                    self.cancel_timer(self.music_handler)
                except Exception:
                    self.log(f"Ikke mulig å stoppe timer for {entity}.")
        if self.light_run_handler is not None:
            if self.timer_running(self.light_run_handler):
                try:
                    self.cancel_timer(self.light_run_handler)
                except Exception:
                    self.log(f"Ikke mulig å stoppe timer for {entity}.")

        timestring =  self.get_state(entity)
        if timestring != '00:00:00':
            self.music_handler = self.run_daily(self.wake_up_music, timestring)
            if self.light_time_offset != 0:
                timeToAdd = datetime.timedelta(minutes = self.light_time_offset)
                newtime = self.parse_datetime(timestring) + timeToAdd
                timestring = str(newtime.time())
            self.light_run_handler = self.run_daily(self.wake_up_with_lights, timestring)

    def wake_up_music(self, kwargs):
        """ Starts music list
        """
        if (
            (self.get_state(self.workday) == 'on'
            or self.get_state(self.alarm_switch_non_work_day, namespace = self.HASS_namespace) == 'on')
            and self.get_state(self.away_state, namespace = self.HASS_namespace) == 'off'
            and self.get_state(self.alarm_switch, namespace = self.HASS_namespace) == 'on'
        ):
            for condition in self.conditions:
                if not eval(condition):
                    return False

            if self.volume != 0:
                self.call_service('media_player/volume_set',
                    entity_id = self.media_player,
                    volume_level = self.volume,
                    namespace = self.HASS_namespace
                )
            self.call_service('media_player/play_media',
                entity_id = self.media_player,
                media_content_id = self.playlist,
                media_content_type = 'music',
                namespace = self.HASS_namespace
            )

    def wake_up_with_lights(self, kwargs):
        """ Turns on lights
        """
        if (
            (self.get_state(self.workday) == 'on'
            or self.get_state(self.alarm_switch_non_work_day, namespace = self.HASS_namespace) == 'on')
            and self.get_state(self.away_state, namespace = self.HASS_namespace) == 'off'
            and self.get_state(self.alarm_switch, namespace = self.HASS_namespace) == 'on'
        ):
            for condition in self.conditions:
                if not eval(condition):
                    return False

            for light in self.wake_up_MQTTlights:
                payload = json.dumps(self.light_data)
                self.mqtt.mqtt_publish(
                    topic = str(light) + "/set",
                    payload = payload,
                    namespace = self.MQTT_namespace
                )
            for light in self.wake_up_lights:
                self.turn_on(light, **self.light_data,
                    namespace = self.HASS_namespace
                )
