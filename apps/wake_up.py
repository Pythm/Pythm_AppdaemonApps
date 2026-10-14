""" Play music and turn on lights to wake up.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.2.0"

from appdaemon import adbase as ad
import datetime
import json
import holidays

class WakeUp(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()

        # Namespaces for HASS and MQTT
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')
        self.MQTT_namespace:str = self.args.get('MQTT_namespace', 'mqtt')
        self.mqtt = None

        self.music_handler = None
        self.light_run_handler = None

        # Set up holidays. Optional: without country_code only weekends are non-work days.
        self.country_code = self.args.get('country_code', None)
        self.holidays = None
        if self.country_code is not None:
            self._set_holidays(self.country_code)

        # Set up vacation
        vacation = self.args.get('vacation', 'input_boolean.vacation')
        vacation_state = self.ADapi.get_state(vacation, namespace = self.HASS_namespace)
        if vacation_state is not None:
            self.away_state = vacation_state == 'on'
            self.ADapi.listen_state(
                self._awayStateListen,
                vacation,
                namespace=self.HASS_namespace
            )
        else:
            self.away_state = False
            if 'vacation' in self.args:
                self.ADapi.log(f"{self.name}: vacation {vacation} was not found.", level = 'WARNING')

        # Set up alarms
        self.alarm_switch = self._setup_switch('alarm_switch', 'input_boolean.alarm_switch',
                                               default = True, listener = self._alarmStateListen)
        self.alarm_switch_non_work_day = self._setup_switch('alarm_switch_non_work_day',
                                                            'input_boolean.alarm_switch_non_work_day',
                                                            default = False, listener = self._alarm_non_work_dayStateListen)

        self.media_player = self.args['media_player']
        self.playlist = self.args['playlist']
        self.volume = self.args.get('volume', None)

        self.wake_up_lights:list = self.args.get('wake_up_lights',[])
        self.wake_up_MQTTlights:list = self.args.get('wake_up_MQTTlights',[])
        if self.wake_up_MQTTlights:
            self.mqtt = self.get_plugin_api('MQTT')

        # Color, brightness and so on. A copy, so the configuration is left alone.
        self.light_data:dict = dict(self.args.get('light_data', {}))

        self.light_time_offset = self.args.get('light_time_offset',0)

        # Home Assistant input_datetime helper with time only
        wake_up_time = self.args['time']
        self.ADapi.listen_state(self._set_wake_up_time, wake_up_time,
            namespace = self.HASS_namespace,
            duration = 5
        )
        self._schedule_alarm(self.ADapi.get_state(wake_up_time, namespace = self.HASS_namespace))

        self.conditions:list = self.args.get('conditions',[])

    def _setup_switch(self, key:str, guess:str, default:bool, listener) -> bool:
        """ Returns the state of the switch in the configuration (or of a helper with the usual name).
            Without any switch the default is used. """

        entity = self.args.get(key, None)
        if entity is None:
            if self.ADapi.entity_exists(guess, namespace = self.HASS_namespace):
                entity = guess
            else:
                return default
        state = self.ADapi.get_state(entity, namespace = self.HASS_namespace)
        if state is None:
            self.ADapi.log(f"{self.name}: {key} {entity} was not found.", level = 'WARNING')
        self.ADapi.listen_state(listener, entity, namespace = self.HASS_namespace)
        return state == 'on'

    def _set_holidays(self, country_code:str) -> None:
        try:
            self.holidays = holidays.country_holidays(str(country_code).upper())
        except (NotImplementedError, KeyError, AttributeError):
            self.ADapi.log(
                f"{self.name}: No holidays found for country_code {country_code}. Only weekends count as non-work days.",
                level = 'WARNING'
            )

    def _cancel_alarm(self) -> None:
        for handler in (self.music_handler, self.light_run_handler):
            if handler is not None:
                self.ADapi.cancel_timer(handler, silent = True)
        self.music_handler = None
        self.light_run_handler = None

    def _schedule_alarm(self, timestring) -> None:
        """ Plans the music and the lights. 00:00:00 turns the alarm off.
            A value that is not a time (unknown, unavailable) leaves the plan as it was. """

        try:
            wake_up_time = self.ADapi.parse_time(timestring)
        except (TypeError, ValueError, NotImplementedError):
            if timestring not in (None, 'unknown', 'unavailable'):
                self.ADapi.log(f"{self.name}: time '{timestring}' is not a time.", level = 'WARNING')
            return

        self._cancel_alarm()
        if wake_up_time == datetime.time(0, 0, 0):
            return
        self.music_handler = self.ADapi.run_daily(self.wake_up_music, wake_up_time)
        light_time = wake_up_time
        if self.light_time_offset != 0:
            timeToAdd = datetime.timedelta(minutes = self.light_time_offset)
            light_time = (datetime.datetime.combine(datetime.date.today(), wake_up_time) + timeToAdd).time()
        self.light_run_handler = self.ADapi.run_daily(self.wake_up_with_lights, light_time)

    def _set_wake_up_time(self, entity, attribute, old, new, kwargs):
        self._schedule_alarm(new)

    def _alarm_active(self) -> bool:
        """ Not on vacation, and the switch for the kind of day decides:
            alarm_switch on a workday, alarm_switch_non_work_day on a holiday or weekend. """

        if self.away_state:
            return False
        if self._is_holiday(self.ADapi.get_now().date()):
            return self.alarm_switch_non_work_day
        return self.alarm_switch

    def _conditions_met(self) -> bool:
        """ Every condition is Python code from the configuration. It runs with this app as self,
            for example: self.ADapi.get_state('person.me') == 'home' """

        for condition in self.conditions:
            try:
                if not eval(condition):
                    return False
            except Exception as e:
                self.ADapi.log(f"{self.name}: Condition '{condition}' failed: {e}. Not waking up.", level = 'ERROR')
                return False
        return True

    def wake_up_music(self, **kwargs):
        """ Starts music list """

        if self._alarm_active() and self._conditions_met():
            if self.volume is not None:
                self.ADapi.call_service('media_player/volume_set',
                    entity_id = self.media_player,
                    volume_level = self.volume,
                    namespace = self.HASS_namespace
                )
            self.ADapi.call_service('media_player/play_media',
                entity_id = self.media_player,
                media_content_id = self.playlist,
                media_content_type = 'music',
                namespace = self.HASS_namespace
            )

    def wake_up_with_lights(self, **kwargs):
        """ Turns on lights """

        if self._alarm_active() and self._conditions_met():
            if self.mqtt is not None:
                # zigbee2mqtt wants "state": "ON" in the payload
                payload = json.dumps({**self.light_data, "state" : "ON"})
                for light in self.wake_up_MQTTlights:
                    self.mqtt.mqtt_publish(
                        topic = str(light) + "/set",
                        payload = payload,
                        namespace = self.MQTT_namespace
                    )
            for light in self.wake_up_lights:
                self.ADapi.call_service('homeassistant/turn_on',
                    entity_id = light,
                    namespace = self.HASS_namespace,
                    **self.light_data
                )

    def _awayStateListen(self, entity, attribute, old, new, kwargs) -> None:
        self.away_state = new == 'on'

    def _alarmStateListen(self, entity, attribute, old, new, kwargs) -> None:
        self.alarm_switch = new == 'on'

    def _alarm_non_work_dayStateListen(self, entity, attribute, old, new, kwargs) -> None:
        self.alarm_switch_non_work_day = new == 'on'

    def _is_holiday(self, date):
        if self.holidays is not None and date in self.holidays:
            return True
        return date.weekday() > 4
