""" Notify on drop in electricity usage (finished program) on Appliances

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.0.3"

from appdaemon.plugins.hass.hassapi import Hass

class Dryer(Hass):

    def initialize(self):
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.get_app(name_of_notify_app)
        self.notify_reciever = self.args['notify_reciever']
        self.notify_title = self.args['notify_title']
        self.notify_message = self.args['notify_message']

        self.dryer_switch = self.args.get('dryer_switch', None)
        self.dryer_power = self.args['dryer_power']

        self.listen_state(self.dryer_is_running, self.dryer_power,
            constrain_state=lambda x: float(x) > 100,
            duration = 30,
            oneshot = True
        )

    def dryer_is_running(self, entity, attribute, old, new, kwargs):
        """ Reacts to powerconsumption and waiting for it to fall again
        """
        self.listen_state(self.dryer_is_stopping, self.dryer_power,
            constrain_state=lambda x: float(x) < 15,
            duration = 30,
            oneshot = True
        )

    def dryer_is_stopping(self, entity, attribute, old, new, kwargs):
        """ Reacts to powerconsumption falling and notifies.
        """
        if self.dryer_switch is not None:
            #TODO: Ask to turn off
            #self.turn_off(self.dryer_switch)
            pass
        self.notify_app.send_notification(
            message = self.notify_message,
            message_title = self.notify_title,
            message_recipient = self.notify_reciever,
            also_if_not_home = False
        )

        self.listen_state(self.dryer_is_running, self.dryer_power,
            constrain_state=lambda x: float(x) > 100,
            duration = 30,
            oneshot = True
        )