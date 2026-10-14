""" Simultaneous Door / Window Guard

Check if two sensors(door/windows) are on/opened at the same time

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.2.0"

from appdaemon import adbase as ad

from ad_config import Sensor
from utils_apps import cancel_listen_handler

# The main sensors have to be open at least this many seconds before the door is checked
MIN_SENSOR_DELAY = 71

class SimultaneousOpen(ad.ADBase):

    def initialize(self):
        
        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.notify_app is None:
            self.ADapi.log(f"{self.name}: Could not find app '{name_of_notify_app}'. Add it to 'dependencies'. Aborting setup", level = 'ERROR')
            return

        self.notify_receiver = self.args.get('notify_receiver', True)
        self.notify_title = self.args.get('notify_title', 'Both door and window is open')
        self.notify_message = self.args.get('notify_message', 'Close either')
        self.also_if_not_home:bool = self.args.get('also_if_not_home', False)

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.simultaneous_switch = self.args.get('simultaneous_switch', None) # HA input_boolean that turns on when both are open

        # Simultaneous doors/windows. Required, a missing key stops the app with a KeyError.
        self.simultaneous_sensor = self.args['simultaneous_sensor']
        # Seconds the second sensor has to be open before it counts
        self.simultaneous_delay:int = int(self.args.get('simultaneous_delay', 60))

        self.ADapi.listen_state(self.sensor_closed, self.simultaneous_sensor,
            new = 'off',
            namespace = self.HASS_namespace
        )
        self.simultaneous_handler = None

        # Get sensors
        self.sensors = [Sensor.from_yaml(item) for item in self.args.get('sensors', [])]
        for sensor in self.sensors:
            if sensor.delay < MIN_SENSOR_DELAY:
                sensor.delay = MIN_SENSOR_DELAY
            self.ADapi.listen_state(self.openedForDuration, sensor.sensor,
                new = 'on',
                duration = sensor.delay,
                namespace = self.HASS_namespace
            )
            self.ADapi.listen_state(self.sensor_closed, sensor.sensor,
                new = 'off',
                namespace = self.HASS_namespace
            )
            # A sensor that is open when the app starts is checked after its delay
            if self.ADapi.get_state(sensor.sensor, namespace = self.HASS_namespace) == 'on':
                self.ADapi.run_in(self._startup_check, sensor.delay)

        # Set valid temperature sensor
        self.check_below_temp = self.args.get('check_below_temp', 23)
        self.temperature_sensor = self.args.get('temperature_sensor', None)

        # Climate with fan only
        self.heater = self.args.get('climate', None)

    def _startup_check(self, **kwargs) -> None:
        self.openedForDuration(None, None, None, None)

    def _door_open(self) -> bool:
        """ The second sensor is on (open) """

        return self.ADapi.get_state(self.simultaneous_sensor, namespace = self.HASS_namespace) == 'on'

    def _any_main_sensor_open(self) -> bool:
        """ At least one of the main sensors is on (open) """

        for sensor in self.sensors:
            if self.ADapi.get_state(sensor.sensor, namespace = self.HASS_namespace) == 'on':
                return True
        return False

    def openedForDuration(self, entity, attribute, old, new, **kwargs) -> None:
        """ Callback when a main sensor has been open for given duration """

        if self._door_open():
            self.both_sensors_opened()
        else:
            # Waits for the second sensor. Stays until all the main sensors are closed,
            # so the second sensor can be opened again.
            cancel_listen_handler(ADapi = self.ADapi, handler = self.simultaneous_handler, name = self.simultaneous_sensor)
            self.simultaneous_handler = self.ADapi.listen_state(self.second_sensor_opened, self.simultaneous_sensor,
                new = 'on',
                duration = self.simultaneous_delay,
                namespace = self.HASS_namespace
            )

    def second_sensor_opened(self, entity, attribute, old, new, **kwargs) -> None:
        """ Callback when second sensor is opened """

        self.both_sensors_opened()

    def both_sensors_opened(self) -> None:
        """ Both a main sensor and a simultaneous sensor are on (open) """

        if not (self._door_open() and self._any_main_sensor_open()):
            return

        if self.simultaneous_switch is not None:
            self.ADapi.call_service('homeassistant/turn_on',
                    entity_id = self.simultaneous_switch,
                    namespace = self.HASS_namespace,
                )

        temp = 0
        if self.temperature_sensor is not None:
            try:
                temp = float(self.ADapi.get_state(self.temperature_sensor,
                    namespace = self.HASS_namespace)
                )
            except (TypeError, ValueError) as val:
                temp = self.check_below_temp
                self.ADapi.log(
                    f"Error when window open. Could not convert {self.temperature_sensor} to number: {val}",
                    level = 'DEBUG'
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

        main_sensor_open = self._any_main_sensor_open()
        if self._door_open() and main_sensor_open:
            return

        # Only stop waiting for the second sensor when all the main sensors are closed
        if not main_sensor_open:
            if cancel_listen_handler(ADapi = self.ADapi, handler = self.simultaneous_handler, name = self.simultaneous_sensor):
                self.simultaneous_handler = None

        if self.simultaneous_switch is not None:
            self.ADapi.call_service('homeassistant/turn_off',
                entity_id = self.simultaneous_switch,
                namespace = self.HASS_namespace,
            )

        # Also to people who are away now, they may have got the notification before they left
        data = {
            'tag' : str(self.name),
            }
        self.notify_app.send_notification(
            message = "clear_notification",
            message_title = self.notify_title,
            message_recipient = self.notify_receiver,
            also_if_not_home = True,
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
            also_if_not_home = self.also_if_not_home,
            data = data
        )
