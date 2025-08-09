""" Check if sensors(door/windows) are on/opened for more than a certain time when the humidity is back down to normal

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.2.0"

from appdaemon import adbase as ad

class BathroomWindow(ad.ADBase):

    def initialize(self):

        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        self.notify_reciever = self.args['notify_reciever']
        self.notify_title = self.args['notify_title']
        self.notify_message = self.args['notify_message']

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.listen_handler = None
        self.timer_handler = None

        # Get sensors
        self.sensors = self.args['sensors']
        for sensor in self.sensors:
            if not 'duration' in sensor:
                sensor['duration'] = 1200
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
        
        # Set humidity data
        self.humidity_sensor = self.args.get('humidity', None)
        if self.humidity_sensor is not None:
            self.humidity_avg_list = []
            self.humidity = self.ADapi.get_state(self.humidity_sensor,
                                                 namespace = self.HASS_namespace)
            try:
                self.humidity_avg_list.append(float(self.humidity))
                self.humidity_average = self.humidity
            except (TypeError, ValueError):
                self.humidity = 50
                self.humidity_average = 50
            self.ADapi.listen_state(self._on_humidity_update,
                                    self.humidity_sensor,
                                    namespace = self.HASS_namespace)

        # Set valid temperature sensor
        self.check_below_temp = self.args.get('check_below_temp', 20)
        self.out_temp:float = 19

        self.turn_off_notifications:str = 'turn_off_notification_' + str(self.name)
        self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action", namespace = self.HASS_namespace)

        self.ADapi.listen_event(self._weather_event, 'WEATHER_CHANGE',
            namespace = self.HASS_namespace
        )

    def _weather_event(self, event_name, data, kwargs) -> None:
        try:
            self.out_temp = float(data['temp'])
        except ValueError:
            return

    def _has_been_opened_for_duration(self, entity, attribute, old, new, kwargs) -> None:
        """ Checks related to windows and humidity sensors
        """
        duration = int(kwargs['time_to_recheck'])
        self._cancel_timer_handler()
        self._checkHumidity(
            time_to_recheck = duration
        )

    def _checkHumidity(self, **kwargs) -> None:
        duration = int(kwargs['time_to_recheck'])

        if self.out_temp <= self.check_below_temp:

            if self.humidity <= self.humidity_average + 10:
                for sensor in self.sensors:
                    if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                        self._send_notification()
                        self._reschedule_check(time_to_recheck = duration)
                        return
            else:
                if self.listen_handler is not None:
                    try:
                        self.ADapi.cancel_listen_state(self.listen_handler)
                    except Exception as exc:
                        self.ADapi.log(f"Could not stop hander in Bathroom Window {self.listen_handler}. Exception: {exc}", level = 'INFO') # DEBUG
                self.listen_handler = self.ADapi.listen_state(self.humidityBelowAvg, self.humidity_sensor,
                    constrain_state=lambda x: float(x) <= self.humidity_average + 10,
                    time_to_recheck = duration,
                    namespace = self.HASS_namespace
                )

    def humidityBelowAvg(self, entity, attribute, old, new, kwargs):
        duration = int(kwargs['time_to_recheck'])
        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                self._send_notification()
                self._reschedule_check(time_to_recheck = duration)
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
            message_title = self.notify_title + " " + str(self.humidity),
            message_recipient = self.notify_reciever,
            also_if_not_home = False,
            data = data
        )
        self.ADapi.log(f"Sent notificatio on bath window with humidity {self.humidity} below avg {self.humidity_average} +10") ###

    def _window_closed(self, entity, attribute, old, new, kwargs):
        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                return
        if self.listen_handler is not None:
            try:
                self.ADapi.cancel_listen_state(self.listen_handler)
            except Exception as exc:
                self.ADapi.log(f"Could not stop hander in Batroom Window {self.listen_handler}. Exception: {exc}", level = 'INFO') # DEBUG
            self.listen_handler = None

        data = {
            'tag' : str(self.name),
            }
        self.notify_app.send_notification(
            message = "clear_notification",
            message_title = self.notify_title,
            message_recipient = self.notify_reciever,
            also_if_not_home = False,
            data = data
        )

    def _on_humidity_update(self, entity, attribute, old, new, kwargs):
        try:
            self.humidity = float(new)
        except (TypeError, ValueError):
            return

        self.humidity_avg_list.append(self.humidity)
        self.humidity_average = sum(self.humidity_avg_list) / len(self.humidity_avg_list)
  
    def _cancel_timer_handler(self):
        if self.timer_handler is not None:
            if self.ADapi.timer_running(self.timer_handler):
                try:
                    self.ADapi.cancel_timer(self.timer_handler)
                except Exception as exc:
                    self.ADapi.log(f"Could not stop hander in {self.name}. Exception: {exc}", level = 'DEBUG')
            self.timer_handler = None

    def _notify_event(self, event_name, data, kwargs) -> None:
        if data['action'] == self.turn_off_notifications:
            self._cancel_timer_handler()

            data = {
                'tag' : str(self.name),
                }
            self.notify_app.send_notification(
                message = "clear_notification",
                message_title = self.notify_title,
                message_recipient = self.notify_reciever,
                also_if_not_home = False,
                data = data
            )