""" Simultaneous Door / Window Guard

Check if two sensors(door/windows) are on/opened at the same time

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.2.0"

from appdaemon import adbase as ad

from ad_config import Sensor

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

        # Get sensors
        self.sensors = [Sensor.from_yaml(item) for item in self.args.get('sensors', [])]
        for sensor in self.sensors:
            if sensor.delay < 70:
                sensor.delay = 71
            self.ADapi.listen_state(self.openedForDuration, sensor.sensor,
                new = 'on',
                duration = sensor.delay,
                sensor = sensor,
                namespace = self.HASS_namespace
            )
            self.ADapi.listen_state(self.sensor_closed, sensor.sensor,
                new = 'off',
                sensor = sensor,
                namespace = self.HASS_namespace
            )

        # Set valid temperature sensor
        self.check_below_temp = self.args.get('check_below_temp', 23)
        self.temperature_sensor = self.args.get('temperature_sensor', None)

        # Climate with fan only
        self.heater = self.args.get('climate', None)

    def openedForDuration(self, entity, attribute, old, new, **kwargs) -> None:
        sensor = kwargs['sensor']
        
        both_open:bool = self.check_second_sensor_open()
        if both_open:
            self.both_sensors_opened()

        else:
            sensor.handler = self.ADapi.listen_state(self.second_sensor_opened, self.simultaneous_sensor,
                new = 'on',
                duration = sensor.delay,
                namespace = self.HASS_namespace
            )

    def second_sensor_opened(self, entity, attribute, old, new, **kwargs):
        self.both_sensors_opened()


    def check_second_sensor_open() -> bool:

        if self.ADapi.get_state(self.simultaneous_sensor, namespace = self.HASS_namespace) == 'on':
            return True

        return False

    def both_sensors_opened(self):
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

        if temp < self.check_below_temp:
            if self.heater is not None:
                ac_state = self.ADapi.get_state(self.heater, namespace = self.HASS_namespace)
                if ac_state == 'fan_only':
                    return
        
        self.notify_about_both_opened()

    def sensor_closed(self, entity, attribute, old, new, kwargs):
        sensor = kwargs['sensor']
        if sensor.handler is not None:
            try:
                self.ADapi.cancel_listen_state(sensor.handler)
            except Exception as exc:
                self.ADapi.log(
                    f"Could not stop hander in doorGuard {self.handler}. Exception: {exc}",
                    level = 'DEBUG'
                )
            sensor.handler = None

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

    def notify_about_both_opened(self):

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