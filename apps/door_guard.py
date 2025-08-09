""" DoorGuard

Check if sensors(door/windows) are on/opened for more than a certain time

    @Pythm / https://github.com/Pythm

"""
__version__ = "0.2.0"

from appdaemon import adbase as ad

class DoorGuard(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        self.notify_reciever = self.args['notify_reciever']
        self.notify_title = self.args['notify_title']
        self.notify_message = self.args['notify_message']

        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.timer_handler = None

        # Get sensors
        self.sensors = self.args['sensors']
        for sensor in self.sensors:
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
        self.turn_off_notifications:str = 'turn_off_notification_' + str(self.name)
        self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action", namespace = self.HASS_namespace)

    def _openedForDuration(self, entity, attribute, old, new, **kwargs) -> None:
        """ Reacts to sensors being on for a certain duration
        """
        duration = int(kwargs['time_to_recheck'])
        self._check_if_closed(
            time_to_recheck = duration
        )

    def _check_if_closed(self, **kwargs):
        """ Checks if the sensors has been closed
        """
        duration = int(kwargs['time_to_recheck'])
        for sensor in self.sensors:
            if self.ADapi.get_state(sensor['sensor'], namespace = self.HASS_namespace) == 'on':
                self._send_notification()
                self._cancel_timer_handler()
                self.timer_handler = self.ADapi.run_in(self._check_if_closed, duration,
                    time_to_recheck = duration
                )
                return

    def _send_notification(self):
        data = {
            'tag' : str(self.name),
            'actions' : [{ 'action' : self.turn_off_notifications, 'title' : 'Do not remind me', 'destructive' : True, 'icon' : 'sfsymbols:stop.circle.fill' }]
            }
        self.notify_app.send_notification(
            message = self.notify_message,
            message_title = self.notify_title,
            message_recipient = self.notify_reciever,
            also_if_not_home = False,
            data = data
        )

    def _window_closed(self, entity, attribute, old, new, kwargs):
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

    def _cancel_timer_handler(self):
        if self.timer_handler is not None:
            if self.ADapi.timer_running(self.timer_handler):
                try:
                    self.ADapi.cancel_timer(self.timer_handler)
                except Exception as exc:
                    self.ADapi.log(f"Could not stop hander in doorGuard {self.timer_handler}. Exception: {exc}", level = 'DEBUG')
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