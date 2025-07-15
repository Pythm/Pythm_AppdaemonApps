""" Check if sensors(door/windows) are on/opened for more than a certain time and that the humidity is normal

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.1.1"

from appdaemon import adbase as ad

class BathroomWindow(ad.ADBase):

    def initialize(self):

        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.get_app(name_of_notify_app)
        self.notify_reciever = self.args['notify_reciever']
        self.notify_title = self.args['notify_title']
        self.notify_message = self.args['notify_message']

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.handler = None
        self.timer_handler = None

        # Get sensors
        self.sensors = self.args['sensors']
        for sensor in self.sensors:
            if sensor['duration'] < 70:
                sensor['duration'] = 71
            self.ADapi.listen_state(self.openedForDuration, sensor['sensor'],
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
        self.humidity = self.args.get('humidity', None)
        if self.humidity:
            if 'humidity_minimum' in self.args:
                self.humidityMin = self.args['humidity_minimum']
            else:
                self.humidityMin = 'sensor.' + str(self.name) + '_humidity_minimum'
                if not self.ADapi.entity_exists(self.ADapi.get_entity(self.humidityMin,
                        namespace = self.HASS_namespace)
                    ):
                    self.ADapi.call_service("state/set",
                        entity_id = self.humidityMin,
                        attributes = {'friendly_name' : 'Humidity minimum'},
                        state = 40,
                        namespace = self.HASS_namespace
                    )
                self.ADapi.log(
                    f"'humidity_minimum' not configured. Using entity: {self.humidityMin} with humidity set to 40",
                    level = 'INFO'
                )
            # Refresh values from sensor 180 seconds before duration runs out
            if 'refresh' in self.args:
                for sensor in self.sensors:
                    if int(sensor['duration']) > 180:
                        self.ADapi.listen_state(self.refreshSensorValues, sensor['sensor'],
                            new = 'on',
                            duration = int(sensor['duration']) - 180,
                            namespace = self.HASS_namespace
                        )

        # Set valid temperature sensor
        self.check_below_temp = self.args.get('check_below_temp', 20)
        self.out_temp:float = 19

        self.ADapi.listen_event(self.weather_event, 'WEATHER_CHANGE',
            namespace = self.HASS_namespace
        )

    def weather_event(self, event_name, data, kwargs) -> None:
        """ Listens for weather change from the weather app
        """
        try:
            self.out_temp = float(data['temp'])
        except ValueError:
            return

    def refreshSensorValues(self, entity, attribute, old, new, kwargs) -> None:
        """ Refreshes humidity values from sensor for zwave_js entities
        """
        humidity_min:float = 60
        try:
            humidity = float(self.ADapi.get_state(self.humidity,
                        namespace = self.HASS_namespace)
                    )
            humidity_min = float(self.ADapi.get_state(self.humidityMin,
                        namespace = self.HASS_namespace)
                    ) + 10
        except ValueError:
            return
        except Exception as exc:
            self.ADapi.log(
                f"Exception error when trying to get humidity from {self.humidity} "
                f"and minumum humidity from {self.humidityMin}: {exc}"
                , level = 'WARNING'
            )
            return

        if humidity <= humidity_min:
            self.ADapi.call_service('zwave_js/refresh_value',
                entity_id = self.humidity,
                namespace = self.HASS_namespace
            )

    def openedForDuration(self, entity, attribute, old, new, kwargs) -> None:
        """ Checks related to windows and humidity sensors
        """
        duration = int(kwargs['time_to_recheck'])
        if self.timer_handler is not None:
            if self.ADapi.timer_running(self.timer_handler):
                try:
                    self.ADapi.cancel_timer(self.timer_handler)
                except Exception as e:
                    self.ADapi.log(
                        f"Could not stop handler in {self.name} for {self.humidity}. Exception {e}",
                        level = 'DEBUG'
                    )
        self._checkHumidity(
            time_to_recheck = duration
        )

    def _checkHumidity(self, **kwargs) -> None:
        duration = int(kwargs['time_to_recheck'])

        if self.out_temp <= self.check_below_temp:
            humidity:float = 50
            humidity_min:float = 60
            try:
                humidity = float(self.ADapi.get_state(self.humidity,
                        namespace = self.HASS_namespace)
                    )
                humidity_min = float(self.ADapi.get_state(self.humidityMin,
                        namespace = self.HASS_namespace)
                    ) + 10
            except ValueError as val:
                self._reschedule_check(time_to_recheck = duration)
                return
            except Exception as exc:
                self.ADapi.log(f"Exception when window open and trying to get humitidy. Error: {exc}", level = 'WARNING')
                data = {
                    'tag' : str(self.name)
                    }
                self.notify_app.send_notification(
                    message = "Exception when window open and trying to get humitidy",
                    message_title = self.notify_title,
                    message_recipient = self.notify_reciever,
                    also_if_not_home = False,
                    data = data
                )
                return

            if humidity <= humidity_min:
                for sensor in self.sensors:
                    if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                        self._send_notification()
                        self._reschedule_check(time_to_recheck = duration)
                        return
            else:
                if self.handler is not None:
                    try:
                        self.ADapi.cancel_listen_state(self.handler)
                    except Exception as exc:
                        self.ADapi.log(f"Could not stop hander in Bathroom Window {self.handler}. Exception: {exc}", level = 'INFO') # DEBUG
                    self.handler = None
                self.handler = self.ADapi.listen_state(self.humidityBelowAvg, self.humidity,
                    constrain_state=lambda x: float(x) <= humidity_min,
                    time_to_recheck = duration
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
        if self.timer_handler is not None:
            if self.ADapi.timer_running(self.timer_handler):
                try:
                    self.ADapi.cancel_timer(self.timer_handler)
                except Exception as e:
                    self.ADapi.log(
                        f"Could not stop handler in {self.name} for {self.humidity}. Exception {e}",
                        level = 'DEBUG'
                    )
        self.timer_handler = self.ADapi.run_in(self._checkHumidity, duration,
            time_to_recheck = duration
        )

    def _send_notification(self):
        data = {
            'tag' : str(self.name)
            }
        self.notify_app.send_notification(
            message = self.notify_message,
            message_title = self.notify_title,
            message_recipient = self.notify_reciever,
            also_if_not_home = False,
            data = data
        )

    def _window_closed(self, entity, attribute, old, new, kwargs):
        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                return
        if self.handler is not None:
            try:
                self.ADapi.cancel_listen_state(self.handler)
            except Exception as exc:
                self.ADapi.log(f"Could not stop hander in Batroom Window {self.handler}. Exception: {exc}", level = 'INFO') # DEBUG
            self.handler = None
