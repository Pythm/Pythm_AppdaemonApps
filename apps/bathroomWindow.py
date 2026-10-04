""" Check if sensors(door/windows) are on/opened for more than a certain time when the humidity is back down to normal

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.3.0"

from collections import deque
from statistics import median

from appdaemon import adbase as ad

class BathroomWindow(ad.ADBase):

    def initialize(self):

        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.notify_app is None:
            self.ADapi.log(f"{self.name}: Could not find app '{name_of_notify_app}'. Add it to 'dependencies'. Aborting setup", level = 'ERROR')
            return
        self.notify_receiver = self.args['notify_receiver']
        self.notify_title = self.args.get('notify_title', 'Bathroom Window Open')
        self.notify_message = self.args.get('notify_message', 'Humidity is down to normal')

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.timer_handler = None
        # True while the window is open, the humidity is high and the app waits for it to drop
        self.waiting_for_humidity:bool = False
        self.recheck_duration:int = 1200

        # Get sensors
        sensors = self.args['sensors']
        if isinstance(sensors, dict):
            sensors = [sensors]
        self.sensors = [dict(sensor) for sensor in sensors]
        for sensor in self.sensors:
            sensor.setdefault('duration', 1200)
            self.ADapi.listen_state(self._has_been_opened_for_duration, sensor['sensor'],
                new = 'on',
                duration = sensor['duration'],
                time_to_recheck = sensor['duration'],
                namespace = self.HASS_namespace
            )
            self.ADapi.listen_state(self._window_closed, sensor['sensor'],
                new = 'off',
                namespace = self.HASS_namespace
            )
            # A window that is open when the app starts is checked after its duration
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                self._cancel_timer_handler()
                self.timer_handler = self.ADapi.run_in(self._checkHumidity, int(sensor['duration']),
                    time_to_recheck = int(sensor['duration'])
                )

        # Set humidity data. 'Normal' is the median of the last humidity_samples readings.
        self.humidity_sensor = self.args.get('humidity', None)
        self.humidity_offset = float(self.args.get('offset', 5))
        self.humidity:float | None = None
        self.humidity_readings:deque = deque(maxlen = int(self.args.get('humidity_samples', 500)))
        if self.humidity_sensor is not None:
            self._store_humidity(self.ADapi.get_state(self.humidity_sensor, namespace = self.HASS_namespace))
            self.ADapi.listen_state(self._on_humidity_update,
                                    self.humidity_sensor,
                                    namespace = self.HASS_namespace)

        # Outdoor temperature comes from ad-Weather. Without it the temperature is not checked.
        self.check_below_temp = float(self.args.get('check_below_temp', 20))
        self.out_temp:float | None = None

        self.turn_off_notifications:str = 'turn_off_notification_' + str(self.name)
        self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action",
            action = self.turn_off_notifications,
            namespace = self.HASS_namespace
        )

        self.ADapi.listen_event(self._weather_event, 'WEATHER_CHANGE',
            namespace = self.HASS_namespace
        )

    def _weather_event(self, event_name, data, **kwargs) -> None:
        try:
            self.out_temp = float(data['temp'])
        except (KeyError, TypeError, ValueError):
            pass

    def _has_been_opened_for_duration(self, entity, attribute, old, new, kwargs) -> None:
        """ Checks related to windows and humidity sensors """

        duration = int(kwargs['time_to_recheck'])
        self._cancel_timer_handler()
        self._checkHumidity(
            time_to_recheck = duration
        )

    def _checkHumidity(self, **kwargs) -> None:
        self.recheck_duration = int(kwargs['time_to_recheck'])

        if self.out_temp is not None and self.out_temp > self.check_below_temp:
            return
        if self._humidity_is_normal():
            self._notify_if_open()
        else:
            # _on_humidity_update continues when the humidity is back to normal
            self.waiting_for_humidity = True

    def _humidity_is_normal(self) -> bool:
        """ True without a humidity sensor or while its value is not known. """

        if self.humidity is None or not self.humidity_readings:
            return True
        return self.humidity <= median(self.humidity_readings) + self.humidity_offset

    def _notify_if_open(self) -> None:
        """ Notifies if a window is open and checks again after the duration. """

        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                self._send_notification()
                self._reschedule_check(time_to_recheck = self.recheck_duration)
                return

    def _reschedule_check(self, **kwargs):
        duration = int(kwargs['time_to_recheck'])
        self._cancel_timer_handler()
        self.timer_handler = self.ADapi.run_in(self._checkHumidity, duration,
            time_to_recheck = duration
        )

    def _send_notification(self):
        data = {
            'tag' : str(self.name),
            'actions' : [{ 'action' : self.turn_off_notifications, 'title' : 'Do not remind me', 'destructive' : True, 'icon' : 'sfsymbols:stop.circle.fill' }]
            }
        self.notify_app.send_notification(
            message = self.notify_message,
            message_title = self.notify_title,
            message_recipient = self.notify_receiver,
            also_if_not_home = False,
            data = data
        )

    def _clear_notification(self) -> None:
        # Also to people who are away now, they may have got the notification before they left
        self.notify_app.send_notification(
            message = "clear_notification",
            message_title = self.notify_title,
            message_recipient = self.notify_receiver,
            also_if_not_home = True,
            data = {'tag' : str(self.name)}
        )

    def _window_closed(self, entity, attribute, old, new, kwargs):
        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                return
        self.waiting_for_humidity = False
        self._cancel_timer_handler()
        self._clear_notification()

    def _store_humidity(self, value) -> bool:
        try:
            self.humidity = float(value)
        except (TypeError, ValueError):
            return False
        self.humidity_readings.append(self.humidity)
        return True

    def _on_humidity_update(self, entity, attribute, old, new, kwargs):
        if not self._store_humidity(new):
            return
        if self.waiting_for_humidity and self._humidity_is_normal():
            self.waiting_for_humidity = False
            self._notify_if_open()

    def _cancel_timer_handler(self):
        if self.timer_handler is not None:
            self.ADapi.cancel_timer(self.timer_handler, silent = True)
            self.timer_handler = None

    def _notify_event(self, event_name, data, **kwargs) -> None:
        self.waiting_for_humidity = False
        self._cancel_timer_handler()
        self._clear_notification()
