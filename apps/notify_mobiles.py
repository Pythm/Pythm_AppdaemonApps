"""Notify mobiles and set mode with MODE_CHANGE from iOS app

@Pythm / https://github.com/Pythm
"""

__version__ = "0.3.0"

from typing import Set

from appdaemon import adbase as ad

from mode_names import translations


class Notify_Mobiles(ad.ADBase):
    """AppDaemon component that forwards Home Assistant events to mobile devices."""

    def initialize(self) -> None:
        self.ADapi = self.get_ad_api()
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.recipients = self.args.get('recipients', [])
        if not self.recipients:
            self.ADapi.log(f"{self.name}: No recipients configured. All notifications will be dropped.", level='WARNING')
        if 'email_config' in self.args:
            self.ADapi.log(
                f"{self.name}: email_config is not used. Set up SMTP in Home Assistant and use "
                "send_via: email with the SMTP notify entity as receiver.",
                level='WARNING'
            )

        if 'siri_message' in self.args:
            self.siri_messages = self.args.get('siri_message', [])
            ios_event_name = self.args.get('ios_event', 'ios.lightwand-mode-change')
            self.ADapi.listen_event(self.ios_event, ios_event_name, namespace=self.HASS_namespace)

        for state_change in self.args.get('notify_state_change', []):
            self.ADapi.listen_state(
                self.stateChanged,
                state_change['sensor'],
                namespace=state_change.get('namespace', self.HASS_namespace),
                message=state_change,
            )

    def send_notification(self, **kwargs) -> None:
        """Send a notification to a subset of configured mobile devices.

        Parameters
        ----------
        message : str
            The text that will appear in the notification. Mandatory.
            ``clear_notification`` clears the notification with the same tag
            on mobile_app devices and is not sent to other receivers.
        message_title : str, optional
            Title shown in the notification. Defaults to ``Home Assistant``.
        message_recipient : Union[str, Iterable[str], bool], optional
            * ``True``  - all recipients receive the message (default).
            * ``"person_name"`` - only the recipient whose ``person`` key matches.
            * ``["person1", "person2"]`` - a whitelist.
            * An empty list, ``None`` or ``False`` - nobody.
        also_if_not_home : bool, optional
            If ``False`` (default) and a recipient has a ``tracker`` that is not
            currently ``home`` the notification is skipped for that recipient.
        data : dict, optional
            Extra data passed to the notify service. ``clickAction`` is added
            automatically if missing.
        """
        message = kwargs.get('message')
        if not message:
            self.ADapi.log("send_notification called without a message", level='WARNING')
            return

        message_title = kwargs.get('message_title', 'Home Assistant')
        recipient_filter = kwargs.get('message_recipient', True)
        also_if_not_home = kwargs.get('also_if_not_home', False)

        # Normalise recipient filter: None means everyone, otherwise a set of names
        recipient_set: Set[str] | None
        if recipient_filter is True:
            recipient_set = None
        elif not recipient_filter:
            return
        elif isinstance(recipient_filter, str):
            recipient_set = {recipient_filter}
        else:
            recipient_set = set(recipient_filter)

        # Make sure we do not mutate the caller's dict
        data = dict(kwargs.get('data') or {})
        data.setdefault('clickAction', 'noAction')

        for r in self.recipients:
            # Skip recipients that are not in the whitelist
            if recipient_set is not None and r.get('person') not in recipient_set:
                continue

            # Skip if tracker is not at home (unless forced)
            if r.get('tracker') and not also_if_not_home:
                if self.ADapi.get_state(r['tracker'], namespace=self.HASS_namespace) != 'home':
                    continue

            receivers = r.get('receiver', [])
            if isinstance(receivers, str):
                receivers = [receivers]
            send_via_email = r.get('send_via', 'notify') == 'email'

            for receiver in receivers:
                if message == 'clear_notification':
                    # Only the Companion app understands this message
                    if send_via_email or not str(receiver).startswith('mobile_app_'):
                        continue
                    self.ADapi.call_service(
                        f'notify/{receiver}',
                        namespace=self.HASS_namespace,
                        message=message,
                        data=data,
                    )
                elif send_via_email:
                    # Receiver is a notify entity from the Home Assistant SMTP integration
                    entity_id = receiver if str(receiver).startswith('notify.') else f'notify.{receiver}'
                    email_kwargs = {key: data[key] for key in ('html', 'attachments', 'priority') if key in data}
                    self.ADapi.call_service(
                        'smtp/send_message',
                        namespace=self.HASS_namespace,
                        entity_id=entity_id,
                        message=message,
                        title=message_title,
                        **email_kwargs,
                    )
                else:
                    self.ADapi.call_service(
                        f'notify/{receiver}',
                        namespace=self.HASS_namespace,
                        message=message,
                        title=message_title,
                        data=data,
                    )

    def ios_event(self, event_name, data, **kwargs) -> None:
        """Listen for iOS events configured with ``siri_message``."""
        message_from_ios = data.get("message")
        if message_from_ios is None:
            return

        for message in self.siri_messages:
            if message_from_ios == message.get('message') and 'notify_receiver' in message:
                self.send_notification(
                    message=message.get('notify_message', message_from_ios),
                    message_title=message.get('notify_title', 'Home Assistant'),
                    message_recipient=message['notify_receiver'],
                )
        self.ADapi.fire_event(translations.MODE_CHANGE, mode=message_from_ios, namespace=self.HASS_namespace)

    def stateChanged(self, entity, attribute, old, new, kwargs) -> None:
        """Listen for state changes and forward a notification."""
        message = kwargs['message']
        if 'notify_receiver' in message:
            self.send_notification(
                message=f"{message.get('notify_message', entity)} {new}",
                message_title=message.get('notify_title', 'Home Assistant'),
                message_recipient=message['notify_receiver'],
            )
