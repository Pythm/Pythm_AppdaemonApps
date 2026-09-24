# apps/ad/apps/notify_mobiles.py
"""Notify mobiles and set mode with MODE_CHANGE from iOS app

@Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

import json
from typing import Iterable, Union, Set

from appdaemon import adbase as ad


class Notify_Mobiles(ad.ADBase):
    """AppDaemon component that forwards Home‑Assistant events to iOS devices."""

    def initialize(self) -> None:
        self.ADapi = self.get_ad_api()
        self.event_listen_str: str = 'MODE_CHANGE'

        language = self.args.get('lightwand_language', 'en')
        language_file = self.args.get(
            'language_file', '/conf/apps/Lightwand/translations.json'
        )
        try:
            with open(language_file) as lang:
                translations = json.load(lang)
        except FileNotFoundError:
            self.ADapi.log("Translation file not found", level='DEBUG')
        else:
            self.event_listen_str = translations.get(language, {}).get(
                'MODE_CHANGE', 'MODE_CHANGE'
            )

        self.recipients = self.args.get('recipients', [])
        if 'siri_message' in self.args:
            self.siri_messages = self.args.get('siri_message', [])
            self.ADapi.listen_event(self.ios_event, "ios.lightwand-mode-change")

        notify_state_change = self.args.get('notify_state_change', [])
        for state_change in notify_state_change:
            self.ADapi.listen_state(
                self.stateChanged,
                state_change['sensor'],
                message=state_change,
            )

    def send_notification(self, **kwargs) -> None:
        """Send a notification to a subset of configured mobile devices.

        Parameters
        ----------
        message : str
            The text that will appear in the notification. Mandatory.
        message_title : str, optional
            Title shown in the notification. Defaults to ``Home Assistant``.
        message_recipient : Union[str, Iterable[str], bool], optional
            * ``True``  – all recipients receive the message.
            * ``"person_name"`` – only the recipient whose ``person`` key matches.
            * ``["person1", "person2"]`` – a whitelist.
            Defaults to ``True``.
        also_if_not_home : bool, optional
            If ``False`` (default) and a recipient has a ``tracker`` that is not
            currently ``home`` the notification is skipped for that recipient.
        data : dict, optional
            Extra data passed to the notify service. ``clickAction`` is added
            automatically if missing.
        """
        # 1️⃣  Pull arguments with sane defaults --------------------------------
        message = kwargs.get('message')
        if not message:
            self.ADapi.log("send_notification called without a message", level='WARNING')
            return

        message_title = kwargs.get('message_title', 'Home Assistant')
        recipient_filter = kwargs.get('message_recipient', True)
        also_if_not_home = kwargs.get('also_if_not_home', False)

        # Normalise recipient filter → set of names (empty set ⇒ everyone)
        if recipient_filter is True:
            recipient_set: Set[str] = set()
        else:
            recipient_set = (
                {recipient_filter}
                if isinstance(recipient_filter, str)
                else set(recipient_filter)
            )

        # Data defaults – make sure we don’t mutate the caller’s dict
        data = kwargs.get('data', {}).copy()
        data.setdefault('clickAction', 'noAction')

        # 2️⃣  Loop over configured recipients ---------------------------------
        notified = 0
        for r in self.recipients:
            # 2a. Skip recipients that are not in the whitelist
            if recipient_set and r.get('person') not in recipient_set:
                continue

            # 2b. Skip if tracker is not at home (unless forced)
            if r.get('tracker') and not also_if_not_home:
                if self.ADapi.get_state(r['tracker']) != 'home':
                    continue

            # 2c. Build the service kwargs (title only for normal messages)
            service_kwargs = {
                'message': message,
                'data': data,
            }
            if message != 'clear_notification':
                service_kwargs['title'] = message_title

            # 2d. Send to every configured receiver for this recipient
            for receiver in r.get('receiver', []):
                self.ADapi.call_service(f'notify/{receiver}', **service_kwargs)
                notified += 1

    def ios_event(self, event_name, data, **kwargs) -> None:
        """Listen for iOS events configured with ``siri_message``."""
        message_from_ios = data.get("message")
        if message_from_ios is None:
            return

        for message in self.siri_messages:
            if message_from_ios == message['message']:
                if 'notify_receiver' in message:
                    self.send_notification(
                        message=message['notify_message'],
                        message_title=message['notify_title'],
                        message_recipient=message['notify_receiver'],
                    )
        self.ADapi.fire_event(self.event_listen_str, mode=message_from_ios)

    def stateChanged(self, entity, attribute, old, new, kwargs) -> None:
        """Listen for state changes and forward a notification."""
        message = kwargs['message']
        if 'notify_receiver' in message:
            self.send_notification(
                message=f"{message['notify_message']} {self.ADapi.get_state(entity)}",
                message_title=message['notify_title'],
                message_recipient=message['notify_receiver'],
            )
