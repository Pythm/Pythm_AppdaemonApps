""" Simultaneous Door / Window Guard

Check if two sensors(door/windows) are on/opened at the same time

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.2.0"

from appdaemon import adbase as ad

from ad_config import Sensor
from utils_apps import cancel_listen_handler

class SimultaneousOpen(ad.ADBase):

    def initialize(self):
        
        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)

        self.notify_receiver = self.args.get('notify_receiver', [])
        self.notify_title = self.args.get('notify_title', 'Both door and window is open')
        self.notify_message = self.args.get('notify_message', 'Close either')

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.simultaneous_switch = self.args.get('simultaneous_switch', None) # HA input_boolean that turns on when both are open

        # Simultaneous doors/windows
        self.simultaneous_sensor = self.args.get('simultaneous_sensor', None)
        if self.simultaneous_sensor is None:
            raise Exception(
                f"\n'simultaneous_sensor' not configured in {self.name}.\n"
                "Please add the sensor to use this app.\n"
                "Aborting setup."
            )

        self.ADapi.listen_state(self.sensor_closed, self.simultaneous_sensor,
            new = 'off',
            namespace = self.HASS_namespace
        )
        self.simultaneous_handler = None

        # Get sensors
        self.sensors = [Sensor.from_yaml(item) for item in self.args.get('sensors', [])]
        for sensor in self.sensors:
            if sensor.delay < 70:
                sensor.delay = 71
            self.ADapi.listen_state(self.openedForDuration, sensor.sensor,
                new = 'on',
                duration = sensor.delay,
                namespace = self.HASS_namespace
            )
            self.ADapi.listen_state(self.sensor_closed, sensor.sensor,
                new = 'off',
                namespace = self.HASS_namespace
            )

        # Set valid temperature sensor
        self.check_below_temp = self.args.get('check_below_temp', 23)
        self.temperature_sensor = self.args.get('temperature_sensor', None)

        # Climate with fan only
        self.heater = self.args.get('climate', None)

    def openedForDuration(self, entity, attribute, old, new, **kwargs) -> None:
        """ Callback when sensor has been open for given duration """

        both_open:bool = self.check_second_sensor_open()
        if both_open:
            self.both_sensors_opened()

        else:
            self.simultaneous_handler = self.ADapi.listen_state(self.second_sensor_opened, self.simultaneous_sensor,
                new = 'on',
                duration = 60,
                namespace = self.HASS_namespace
            )

    def second_sensor_opened(self, entity, attribute, old, new, **kwargs) -> None:
        """ Callback when second sensor is opened """

        self.both_sensors_opened()

    def check_second_sensor_open(self) -> bool:
        """ Check if second sensor is on (open) """

        if self.ADapi.get_state(self.simultaneous_sensor, namespace = self.HASS_namespace) == 'on':
            return True

        return False

    def both_sensors_opened(self) -> None:
        """ Both a main sensor and a simultaneous sensor are on (open) """

        self.ADapi.call_service('input_boolean/turn_on',
                entity_id = self.simultaneous_switch,
                namespace = self.HASS_namespace,
            )

        temp = 0
        if self.temperature_sensor is not None:
            try:
                temp = float(self.ADapi.get_state(self.temperature_sensor,
                    namespace = self.HASS_namespace)
                )
            except ValueError as val:
                temp = self.check_below_temp
                self.ADapi.log(
                    f"Error when window open. Could not convert {self.temperature_sensor} to number. ValueError: {val}"
                    , level = 'DEBUG'
                )
            except Exception as exc:
                temp = self.check_below_temp
                self.ADapi.log(
                    f"Error when window open. Could not convert {self.temperature_sensor} to number. Exception: {exc}",
                    level = 'WARNING'
                )

        if temp > self.check_below_temp:
            return
        if self.heater is not None:
            ac_state = self.ADapi.get_state(self.heater, namespace = self.HASS_namespace)
            if ac_state in ['fan_only', 'off']:
                return
        
        self.notify_about_both_opened()

    def sensor_closed(self, entity, attribute, old, new, kwargs) -> None:
        """ A sensor is closed """

        if self.ADapi.get_state(self.simultaneous_sensor, namespace = self.HASS_namespace) == 'on':
            for sensor in self.sensors:
                if self.ADapi.get_state(sensor.sensor, namespace = self.HASS_namespace) == 'on':
                    return

        if cancel_listen_handler(ADapi = self.ADapi, handler = self.simultaneous_handler, name = self.simultaneous_sensor):
            self.simultaneous_handler = None

        self.ADapi.call_service('input_boolean/turn_off',
            entity_id = self.simultaneous_switch,
            namespace = self.HASS_namespace,
        )

        data = {
            'tag' : str(self.name),
            }
        self.notify_app.send_notification(
            message = "clear_notification",
            message_title = self.notify_title,
            message_recipient = self.notify_receiver,
            also_if_not_home = False,
            data = data
        )

    def notify_about_both_opened(self) -> None:
        """ Sends notification """

        data = {
            'tag' : str(self.name)
            }
        self.notify_app.send_notification(
            message = self.notify_message,
            message_title = self.notify_title,
            message_recipient = self.notify_receiver,
            also_if_not_home = False,
            data = data
        )