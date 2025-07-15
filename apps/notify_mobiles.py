""" Notify mobiles and set mode with MODE_CHANGE from ios app

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.4"

from appdaemon.plugins.hass.hassapi import Hass

class Notify_Mobiles(Hass):

    def initialize(self):
        self.event_listen_str:str = 'MODE_CHANGE'

        language = self.args.get('lightwand_language', 'en')
        language_file = self.args.get('language_file', '/conf/apps/Lightwand/translations.json')
        try:
            with open(language_file) as lang:
                translations = json.load(lang)
        except FileNotFoundError:
            self.log("Translation file not found", level = 'DEBUG')
        else:
            self.event_listen_str = translations[language]['MODE_CHANGE']

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

    def send_notification(self, **kwargs) -> None:
        """ Sends notification to recipients via Home Assistant notification.
        """
        message:str = kwargs['message']
        message_title:str = kwargs.get('message_title', 'Home Assistant')
        message_recipient:str = kwargs.get('message_recipient', True)
        also_if_not_home:bool = kwargs.get('also_if_not_home', False)
        data:dict = kwargs.get('data', {'clickAction' : 'noAction'})
    
        for r in self.recipients:
            if (
                r['person'] in message_recipient
                or message_recipient == True
            ):
                if (
                    'tracker' in r
                    and not also_if_not_home
                ):
                    if self.get_state(r['tracker']) != 'home':
                        continue
                for re in r['reciever']:
                    self.call_service(f'notify/{re}',
                        title = message_title,
                        message = message,
                        data = data
                    )

    def ios_event(self, event_name, data, kwargs) -> None:
        """ Listens for ios events configured with "siri message", sends notifications and changes mode.
        """
        message = kwargs['message']
        if 'notify_reciever' in message:
            self.send_notification(
                message = message['notify_message'],
                message_title = message['notify_title'],
                message_recipient = message['notify_reciever']
            )
        self.fire_event(self.event_listen_str, mode = message['message'] )

    def stateChanged(self, entity, attribute, old, new, kwargs) -> None:
        """ Listens for state changes and sends notification
        """
        message = kwargs['message']
        if 'notify_reciever' in message:
            self.send_notification(
                message = f"{message['notify_message']} {self.get_state(entity)}",
                message_title = message['notify_title'],
                message_recipient = message['notify_reciever']
            )