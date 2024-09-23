""" Notify mobiles and set mode with MODE_CHANGE from ios app

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.1"

import appdaemon.plugins.hass.hassapi as hass

class Notify_Mobiles(hass.Hass):

    def initialize(self):
        self.recipients = self.args.get('recipients', [])
        siri_message = self.args.get('siri_message', [])
        for message in siri_message:
            self.listen_event(self.ios_event, "ios.action_fired",
                actionName = message['message'],
                message = message
            )

        notify_state_change = self.args.get('notify_state_change', [])
        for state_change in notify_state_change:
            self.listen_state(self.stateChanged, state_change['sensor'],
                message = state_change
            )


        # Uses the HA notify to send notifications to reciever
    def send_notification(self, message = 'Message', message_title = 'title', message_recipient = ['all'] ):
        for r in self.recipients:
            if (
                r['person'] in message_recipient
                or 'all' in message_recipient
            ):
                if 'tracker' in r:
                    if self.get_state(r['tracker']) != 'home':
                        continue
                for re in r['reciever']:
                    self.notify(f"{message}",
                        title = f"{message_title}",
                        name = f"{re}"
                    )


    def ios_event(self, event_name, data, kwargs):
        message = kwargs['message']
        if 'notify_reciever' in message:
            self.send_notification(message['notify_message'],
                message['notify_title'],
                message['notify_reciever']
            )
        self.fire_event("MODE_CHANGE", mode = message['message'] )


    def stateChanged(self, entity, attribute, old, new, kwargs):
        message = kwargs['message']
        self.send_notification(f"{message['notify_message']}{self.get_state(entity)}",
            message['notify_title'],
            message['notify_reciever']
        ) 