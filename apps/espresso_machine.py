""" Espresso machine

Turns on switch based on datetime input and checks if it is turned off at 15:00

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.1"

from appdaemon.plugins.hass.hassapi import Hass
import datetime

class EspressoMachine(Hass):

    def initialize(self):
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.get_app(name_of_notify_app)
        self.notify_receiver = self.args['notify_receiver']
        self.notify_title = self.args.get('notify_title', 'Coffee')
        self.notify_message = self.args.get('notify_message', 'Coffee machine is still on')

        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.handler = None

        self.espresso_machine = self.args['espresso_machine']
        last_chance = self.args.get('last_chance', '15:00:00')
        self.run_daily(self._check_coffee_machine_is_off, last_chance)

        if 'coffee_timer' in self.args:
            self.coffee_timer = self.args['coffee_timer']
            self.listen_state(self._set_start_up_time, self.coffee_timer,
                duration = 5,
                namespace = self.HASS_namespace
            )
            if self.get_state(self.coffee_timer, namespace = self.HASS_namespace) != '00:00:00':
                self.handler = self.run_daily(self._turn_on_coffee_machine,
                                              self.get_state(self.coffee_timer,
                                                             namespace = self.HASS_namespace))

        self.turn_off_action:str = 'turn_off_' + str(self.espresso_machine)
        self.listen_event(self._notify_event, "mobile_app_notification_action", namespace = self.HASS_namespace)

    def _set_start_up_time(self, entity, attribute, old, new, kwargs) -> None:
        if self.handler is not None:
            if self.timer_running(self.handler):
                try:
                    self.cancel_timer(self.handler)
                except:
                    self.log(f"Ikke mulig å stoppe timer for {entity}.")
            self.handler = None

        if self.get_state(self.coffee_timer, namespace = self.HASS_namespace) != '00:00:00':
            self.handler = self.run_daily(self._turn_on_coffee_machine,
                                          self.get_state(self.coffee_timer,
                                                         namespace = self.HASS_namespace))

    def _turn_on_coffee_machine(self, kwargs) -> None:
        if self.get_state(self.espresso_machine, namespace = self.HASS_namespace) == 'off':
            self.call_service('switch/turn_on',
                              entity_id = self.espresso_machine,
                              namespace = self.HASS_namespace)

    def _check_coffee_machine_is_off(self, kwargs) -> None:
        if self.get_state(self.espresso_machine, namespace = self.HASS_namespace) == 'on':
            data = {
                'tag' : str(self.espresso_machine),
                'actions' : [{ 'action' : self.turn_off_action, 'title' : 'Turn Off', 'destructive' : True }]
                }
            self.notify_app.send_notification(
                message = self.notify_message,
                message_title = self.notify_title,
                message_recipient = self.notify_receiver,
                also_if_not_home = True,
                data = data
            )

    def _notify_event(self, event_name, data, **kwargs) -> None:
        if data['action'] == self.turn_off_action:
            self.call_service('switch/turn_off',
                entity_id = self.espresso_machine,
                namespace = self.HASS_namespace
            )