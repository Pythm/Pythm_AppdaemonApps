""" Play music and turn on lights to wake up.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.1.0"

from appdaemon.plugins.hass.hassapi import Hass
import datetime
import json
from geopy.geocoders import Nominatim
import holidays

class WakeUp(Hass):

    def initialize(self):

        # Namespaces for HASS and MQTT
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.MQTT_namespace:str = self.args.get('MQTT_namespace', 'mqtt')
        self.mqtt = None

        self.music_handler = None
        self.light_run_handler = None

        # Set up holliday
        self.country_code = None
        if 'country_code' in self.args:
            self.country_code = self.args['country_code']
        elif 'latitude' in self.config and 'longitude' in self.config:
            try:
                geolocator = Nominatim(user_agent="ElectricalPriceCalc")
                location = geolocator.reverse((self.config['latitude'], self.config['longitude']), language='en')
                self.country_code = location.raw['address'].get('country_code', 'NO')
                self.log(f"Country code set to {self.country_code.upper()} in {self.name}", level = 'INFO')
            except Exception as e:
                self.log(f"Failed to get country code from geolocation: {e}", level='ERROR')

        if self.country_code is not None:
            try:
                holiday_class = getattr(holidays, self.country_code.upper())
                self.holidays = holiday_class(years=[datetime.date.today().year, datetime.date.today().year + 1])
            except AttributeError:
                self.log(f"Could not find holidays for {self.country_code}, defaulting to Norway.", level = 'INFO')
                self.holidays = holidays.Norway(years=[datetime.date.today().year, datetime.date.today().year + 1])

        # Set up vacation
        if 'vacation' in self.args:
            away_state = self.args['vacation']
        else:
            away_state = None
            if self.entity_exists('input_boolean.vacation',
                namespace = self.HASS_namespace
            ):
                away_state = 'input_boolean.vacation'
        if away_state is None:
            self.away_state = False
        else:
            self.away_state = self.get_state(away_state, namespace = self.HASS_namespace)  == 'on'
            self.listen_state(self._awayStateListen, away_state,
                namespace = self.HASS_namespace
            )

        # Set up alarms
        if 'alarm_switch' in self.args:
            alarm_switch = self.args['alarm_switch']
        else:
            alarm_switch = None
            if self.entity_exists('input_boolean.alarm_switch',
                namespace = self.HASS_namespace
            ):
                alarm_switch = 'input_boolean.alarm_switch'
        if alarm_switch is None:
            self.alarm_switch = True
        else:
            self.alarm_switch = self.get_state(alarm_switch, namespace = self.HASS_namespace)  == 'on'
            self.listen_state(self._alarmStateListen, alarm_switch,
                namespace = self.HASS_namespace
            )

        if 'alarm_switch_non_work_day' in self.args:
            alarm_switch_non_work_day = self.args['alarm_switch_non_work_day']
        else:
            alarm_switch_non_work_day = None
            if self.entity_exists('input_boolean.alarm_switch_non_work_day',
                namespace = self.HASS_namespace
            ):
                alarm_switch_non_work_day = 'input_boolean.alarm_switch_non_work_day'
        if alarm_switch_non_work_day is None:
            self.alarm_switch_non_work_day = False
        else:
            self.alarm_switch_non_work_day = self.get_state(alarm_switch_non_work_day, namespace = self.HASS_namespace)  == 'on'
            self.listen_state(self._alarm_non_work_dayStateListen, alarm_switch_non_work_day,
                namespace = self.HASS_namespace
            )

        self.media_player = self.args['media_player']
        self.playlist = self.args['playlist']
        self.volume = self.args.get('volume', None)

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
            self.listen_state(self._set_wake_up_time, wake_up_time,
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

    def _set_wake_up_time(self, entity, attribute, old, new, kwargs):
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
            not self.away_state and
            (
                (self._is_holiday(datetime.date.today()) and self.alarm_switch_non_work_day)
                or (not self._is_holiday(datetime.date.today()) and self.alarm_switch)
            )
        ):
            for condition in self.conditions:
                if not eval(condition):
                    return False
            if self.volume is not None:
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
            (self._is_holiday(datetime.date.today())
            or self.alarm_switch_non_work_day)
            and not self.away_state
            and self.alarm_switch
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

    def _awayStateListen(self, entity, attribute, old, new, kwargs) -> None:
        self.away_state = new == 'on'

    def _alarmStateListen(self, entity, attribute, old, new, kwargs) -> None:
        self.alarm_switch = new == 'on'

    def _alarm_non_work_dayStateListen(self, entity, attribute, old, new, kwargs) -> None:
        self.alarm_switch_non_work_day = new == 'on'

    def _is_holiday(self, date):
        return date in self.holidays