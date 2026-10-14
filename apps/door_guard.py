""" DoorGuard

Check if sensors(door/windows) are on/opened for more than a certain time

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.3.0"

from appdaemon import adbase as ad

class DoorGuard(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.notify_app is None:
            self.ADapi.log(f"{self.name}: Could not find app '{name_of_notify_app}'. Add it to 'dependencies'. Aborting setup", level = 'ERROR')
            return
        self.notify_receiver = self.args['notify_receiver']
        self.notify_title = self.args['notify_title']
        self.notify_message = self.args['notify_message']
        self.also_if_not_home:bool = self.args.get('also_if_not_home', False)

        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.timer_handler = None

        # Get sensors
        sensors = self.args['sensors']
        if isinstance(sensors, dict):
            sensors = [sensors]
        self.sensors = [dict(sensor) for sensor in sensors]
        for sensor in self.sensors:
            sensor.setdefault('duration', 300)
            self.ADapi.listen_state(self._openedForDuration, sensor['sensor'],
                new = 'on',
                duration = sensor['duration'],
                time_to_recheck = sensor['duration'],
                namespace = self.HASS_namespace
            )
            self.ADapi.listen_state(self._window_closed, sensor['sensor'],
                new = 'off',
                namespace = self.HASS_namespace
            )
            # Something that is open when the app starts is checked after its duration
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                self._cancel_timer_handler()
                self.timer_handler = self.ADapi.run_in(self._check_if_closed, int(sensor['duration']),
                    time_to_recheck = int(sensor['duration'])
                )
        self.turn_off_notifications:str = 'turn_off_notification_' + str(self.name)
        self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action",
            action = self.turn_off_notifications,
            namespace = self.HASS_namespace
        )

    def _openedForDuration(self, entity, attribute, old, new, **kwargs) -> None:
        duration = int(kwargs['time_to_recheck'])
        self._check_if_closed(
            time_to_recheck = duration
        )

    def _check_if_closed(self, **kwargs):
        duration = int(kwargs['time_to_recheck'])
        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                self._send_notification(sensor['sensor'])
                self._cancel_timer_handler()
                self.timer_handler = self.ADapi.run_in(self._check_if_closed, duration,
                    time_to_recheck = duration
                )
                return

    def _send_notification(self, entity:str):
        # {sensor} in the message is replaced with the name of the sensor that is open
        name = self.ADapi.get_state(entity, attribute = 'friendly_name', namespace = self.HASS_namespace) or entity
        data = {
            'tag' : str(self.name),
            'actions' : [{ 'action' : self.turn_off_notifications, 'title' : 'Do not remind me', 'destructive' : True, 'icon' : 'sfsymbols:stop.circle.fill' }]
            }
        self.notify_app.send_notification(
            message = self.notify_message.replace('{sensor}', str(name)),
            message_title = self.notify_title,
            message_recipient = self.notify_receiver,
            also_if_not_home = self.also_if_not_home,
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
        # Keep reminding while another sensor is still open
        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                return
        self._cancel_timer_handler()
        self._clear_notification()

    def _cancel_timer_handler(self):
        if self.timer_handler is not None:
            self.ADapi.cancel_timer(self.timer_handler, silent = True)
            self.timer_handler = None

    def _notify_event(self, event_name, data, **kwargs) -> None:
        if data.get('action') != self.turn_off_notifications:
            return
        self._cancel_timer_handler()
        self._clear_notification()
