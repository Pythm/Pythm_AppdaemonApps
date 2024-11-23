""" Notify mobiles and set mode with MODE_CHANGE from ios app

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.2"

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


    def send_notification(self,
        message:str = '',
        message_title:str = '',
        message_recipient:str = '',
        also_if_not_home:bool = False
    ) -> None:
        """ Sends notification to recipients via Home Assistant notification.
        """
        for r in self.recipients:
            if r['person'] == message_recipient:
                if (
                    'tracker' in r
                    or also_if_not_home   
                ):
                    if self.get_state(r['tracker']) != 'home':
                        continue
                for re in r['reciever']:
                    self.notify(f"{message}",
                        title = f"{message_title}",
                        name = f"{re}"
                    )
                break


    def ios_event(self, event_name, data, kwargs) -> None:
        """ Listens for ios events configured with "siri message", sends notifications and changes mode.
        """
        message = kwargs['message']
        if 'notify_reciever' in message:
            for r in message['notify_reciever']:
                self.send_notification(
                    message = message['notify_message'],
                    message_title = message['notify_title'],
                    message_recipient = r
                )
        self.fire_event("MODE_CHANGE", mode = message['message'] )


    def stateChanged(self, entity, attribute, old, new, kwargs) -> None:
        """ Listens for state changes and sends notification
        """
        message = kwargs['message']
        if 'notify_reciever' in message:
            for r in message['notify_reciever']:
                self.send_notification(
                    message = f"{message['notify_message']} - {self.get_state(entity)}",
                    message_title = message['notify_title'],
                    message_recipient = r
                )