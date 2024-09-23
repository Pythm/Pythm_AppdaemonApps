""" Espresso machine

Turns on/off a switch with an ios.action_fired and checks if it is turned off at 15:00

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

import appdaemon.plugins.hass.hassapi as hass
import datetime

class EspressoMachine(hass.Hass):

    handler = None

    def initialize(self):
        self.notify_app = self.get_app('notify_mobiles')
        self.notify_reciever = self.args['notify_reciever']
        self.notify_title = self.args['notify_title']
        self.notify_message = self.args['notify_message']

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

    def set_start_up_time(self, entity, attribute, old, new, kwargs):
        if self.handler != None:
            if self.timer_running(self.handler):
                try:
                    self.cancel_timer(self.handler)
                except:
                    self.log(f"Ikke mulig å stoppe timer for {entity}.")

        if self.get_state(self.coffee_timer) != '00:00:00':
            self.handler = self.run_daily(self.start_up_coffee, self.get_state(self.coffee_timer))

    def start_up_coffee(self, kwargs):
        if (
            self.get_state(self.coffee_timer) != '00:00:00'
            and self.get_state(self.espresso_machine) == 'off'
        ):
            self.call_service('switch/turn_on', entity_id = self.espresso_machine )

    def ios_event(self, event_name, data, kwargs):
        if self.get_state(self.espresso_machine) == 'off':
            if self.now_is_between('06:00:00', '14:30:00'):
                self.call_service('switch/turn_on', entity_id = self.espresso_machine )
        elif self.get_state(self.espresso_machine) == 'on':
            self.call_service('switch/turn_off', entity_id = self.espresso_machine )

    def checkIfStillOn(self, kwargs):
        if self.get_state(self.espresso_machine) == 'on':
            self.notify_app.send_notification(self.notify_message ,self.notify_title , self.notify_reciever)
