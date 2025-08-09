""" Simultaneous Door / Window Guard

Check if two sensors(door/windows) are on/opened at the same time

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.1.1"

from appdaemon import adbase as ad

class SimultaneousOpen(ad.ADBase):

    def initialize(self):
        
        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)

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
            self.ADapi.listen_state(self.cancelListenState, sensor['sensor'],
                new = 'off',
                namespace = self.HASS_namespace
            )

        # Simultaneous doors/windows
        self.simultaneous = self.args.get('simultaneous_sensor', None)

        # Set valid temperature sensor
        self.check_below_temp = self.args.get('check_below_temp', 24)
        self.temperature_sensor = self.args.get('temperature_sensor', None)

    def openedForDuration(self, entity, attribute, old, new, kwargs) -> None:
        """ Window or door has been opened for a given duration. Will check if another window/door is opened
        """
        duration = int(kwargs['time_to_recheck'])
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

        if self.simultaneous:
            if self.ADapi.get_state(self.simultaneous, namespace = self.HASS_namespace) == 'on':

                if temp < self.check_below_temp:
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
                    self.ADapi.run_in(self.recheck_second_door_opened, duration,
                        time_to_recheck = duration
                    )
            else:
                self.handler = self.ADapi.listen_state(self.second_door_opened, self.simultaneous,
                    new = 'on',
                    duration = duration,
                    time_to_recheck = duration,
                    namespace = self.HASS_namespace
                )

    def second_door_opened(self, entity, attribute, old, new, kwargs):
        """ Reacts to the second door/window being opened
        """
        duration = int(kwargs['time_to_recheck'])
        self.ADapi.run_in(self.recheck_second_door_opened, duration,
            time_to_recheck = duration
        )

    def recheck_second_door_opened(self, **kwargs):
        """ Checks if the second door/window is still opened
        """
        duration = int(kwargs['time_to_recheck'])
        
        temp:float = self.check_below_temp
        if self.temperature_sensor is not None:
            try:
                temp = float(self.ADapi.get_state(self.temperature_sensor,
                    namespace = self.HASS_namespace)
                )
            except ValueError as val:
                self.ADapi.log(
                    f"Error when window open. Could not convert {self.temperature_sensor} to number. ValueError: {val}",
                    level = 'DEBUG'
                )
            except Exception as exc:
                self.ADapi.log(
                    f"Error when window open. Could not convert {self.temperature_sensor} to number. Exception: {exc}",
                    level = 'WARNING'
                )

        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor']) == 'on':
                if self.ADapi.get_state(self.simultaneous) == 'on':
                    if temp <= self.check_below_temp:
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
                        self.ADapi.run_in(self.recheck_second_door_opened, duration,
                            time_to_recheck = duration
                        )
                        return

    def cancelListenState(self, entity, attribute, old, new, kwargs):
        """ Cancel listen state
        """
        if self.handler is not None:
            try:
                self.ADapi.cancel_listen_state(self.handler)
            except Exception as exc:
                self.ADapi.log(
                    f"Could not stop hander in doorGuard {self.handler}. Exception: {exc}",
                    level = 'DEBUG'
                )
            self.handler = None

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