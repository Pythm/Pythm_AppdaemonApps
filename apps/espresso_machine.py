""" Espresso machine

Turns on/off a switch with an ios.action_fired and checks if it is turned off at 15:00

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.2"

from appdaemon.plugins.hass.hassapi import Hass
import datetime

class EspressoMachine(Hass):

    def initialize(self):
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.get_app(name_of_notify_app)
        self.notify_reciever = self.args['notify_reciever']
        self.notify_title = self.args['notify_title']
        self.notify_message = self.args['notify_message']

        self.handler = None

        self.espresso_machine = self.args['espresso_machine']
        self.run_daily(self.checkIfStillOn, '15:00:00')

        if 'coffee_timer' in self.args:
            self.coffee_timer = self.args['coffee_timer']
            self.listen_state(self.set_start_up_time, self.coffee_timer,
                duration = 5
            )
            self.handler = self.run_daily(self.start_up_coffee, self.get_state(self.coffee_timer))

        if 'ios_toggle' in self.args:
            self.ios_toggle = self.args['ios_toggle']
            self.listen_event(self.ios_event, "ios.action_fired",
                actionName = self.ios_toggle    
            )

    def set_start_up_time(self, entity, attribute, old, new, kwargs) -> None:
        """ Listens for changes to a HA input_datetime helper and sets time to turn on coffee machine.
        """
        if self.handler is not None:
            if self.timer_running(self.handler):
                try:
                    self.cancel_timer(self.handler)
                except:
                    self.log(f"Ikke mulig å stoppe timer for {entity}.")
            self.handler = None

        if self.get_state(self.coffee_timer) != '00:00:00':
            self.handler = self.run_daily(self.start_up_coffee, self.get_state(self.coffee_timer))

    def start_up_coffee(self, kwargs) -> None:
        """ Turns on coffee machine.
        """
        if (
            self.get_state(self.coffee_timer) != '00:00:00'
            and self.get_state(self.espresso_machine) == 'off'
        ):
            self.turn_on(self.espresso_machine)

    def ios_event(self, event_name, data, kwargs) -> None:
        """ Turns on coffee machine if off or turns off is already on.
        """
        if self.get_state(self.espresso_machine) == 'off':
            if self.now_is_between('06:00:00', '14:30:00'):
                self.call_service('switch/turn_on', entity_id = self.espresso_machine )
        elif self.get_state(self.espresso_machine) == 'on':
            self.call_service('switch/turn_off', entity_id = self.espresso_machine )

    def checkIfStillOn(self, kwargs) -> None:
        """ Sends notification if coffee machine is still on.
        """
        if self.get_state(self.espresso_machine) == 'on':
            self.notify_app.send_notification(
                message = self.notify_message,
                message_title = self.notify_title,
                message_recipient = self.notify_reciever,
                also_if_not_home = True
            )
