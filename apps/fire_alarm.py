""" FireAlarm
Trigger a mode change if fire alarm is triggered.
Turns off switches and opens screens/garagedoors

    @Pythm / https://github.com/Pythm

"""

__version__ = "0.2.0"

from appdaemon import adbase as ad

from mode_names import translations

UNAVAIL = ('unavailable', 'unknown')
# Items in one of these states are not turned off
OFF_STATES = (None, 'off', 'unavailable', 'unknown', 'standby')

def _as_list(value) -> list:
    """ A single entity in the configuration is treated as a list of one. """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)

class FireAlarm(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace:str = self.args.get('HASS_namespace', 'default')

        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.notify_app is None:
            # The rest still works as a fire alarm without notifications
            self.ADapi.log(f"{self.name}: Could not find app '{name_of_notify_app}'. No notifications will be sent. Add it to 'dependencies'.", level = 'ERROR')
        self.notify_receiver = self.args['notify_receiver']

        self.anyone_home = True
        self.mode_management_app = None
        mode_management_app_name = self.args.get('modeManagementApp', None)
        if mode_management_app_name is not None:
            self.mode_management_app = self.ADapi.get_app(mode_management_app_name)
            if self.mode_management_app is None:
                self.ADapi.log(f"{self.name}: Could not find app '{mode_management_app_name}'. Someone is assumed to be home.", level = 'WARNING')

        # True from the first detector that is on until none are on any more
        self.alarms:list = _as_list(self.args['alarms'])
        for alarm in self.alarms:
            self.ADapi.listen_state(self._alarmactivated, alarm,
                namespace = self.HASS_namespace
            )
        # A fire that is going on when the app starts is cleared like any other
        self.fire_active:bool = any(
            self.ADapi.get_state(alarm, namespace = self.HASS_namespace) == 'on' for alarm in self.alarms
        )

        self.turn_off_items:list = _as_list(self.args.get('turn_off', []))
        self.turn_off_media_players:bool = self.args.get('turn_off_media_players', True)

        self.screens:list = _as_list(self.args.get('screens', []))

    def _alarmactivated(self, entity, attribute, old, new, kwargs) -> None:
        if new == 'on':
            self.fire_active = True
            self.ADapi.fire_event(translations.MODE_CHANGE, mode = translations.fire, namespace = self.HASS_namespace)
            self._send_notification(entity)
            self._turn_off_items()
            self._open_screens()

        elif new == 'off':
            self._detector_cleared()

        elif (
            new not in UNAVAIL and
            old not in UNAVAIL
        ):
            self.ADapi.log(
                f"Fire Alarm: {entity}. New: {new}. Old: {old}. Logic not implemented. Please open a issue with this info.",
                level = 'INFO'
            )

    def _send_notification(self, entity:str) -> None:
        if self.notify_app is None:
            return
        name = self.ADapi.get_state(entity, attribute = 'friendly_name', namespace = self.HASS_namespace) or entity
        self.notify_app.send_notification(
            message = f"at {name}",
            message_title = "Smoke detected",
            message_recipient = self.notify_receiver,
            also_if_not_home = True
        )

    def _turn_off_items(self) -> None:
        items = list(self.turn_off_items)
        if self.turn_off_media_players:
            # Looked up now, so players added after the app started are included
            media_players = self.ADapi.get_state('media_player', namespace = self.HASS_namespace) or {}
            for entity_id in media_players:
                if entity_id not in items:
                    items.append(entity_id)
        for item in items:
            try:
                if self.ADapi.get_state(item, namespace = self.HASS_namespace) not in OFF_STATES:
                    self.ADapi.call_service('homeassistant/turn_off',
                        entity_id = item,
                        namespace = self.HASS_namespace
                    )
            except Exception as exc:
                self.ADapi.log(
                    f"Could not turn off {item} when fire alarm was triggered. Exception: {exc}",
                    level = 'WARNING'
                )

    def _open_screens(self) -> None:
        if self.mode_management_app:
            try:
                self.anyone_home = self.mode_management_app.anyone_home()
            except Exception as exc:
                self.anyone_home = True
                self.ADapi.log(f"Could not ask {self.mode_management_app} if anyone is home: {exc}. Someone is assumed to be home.", level = 'WARNING')
        if self.anyone_home:
            for screen in self.screens:
                try:
                    if self.ADapi.get_state(screen, attribute='current_position', namespace = self.HASS_namespace) != 100:
                        self.ADapi.call_service('cover/open_cover',
                            entity_id = screen,
                            namespace = self.HASS_namespace
                        )
                except Exception as exc:
                    self.ADapi.log(
                        f"Could not open {screen} when fire alarm was triggered. Exception: {exc}",
                        level = 'WARNING'
                    )

    def _detector_cleared(self) -> None:
        """ A detector is off. The fire mode ends when no detector is on any more. """

        if not self.fire_active:
            return
        for alarm in self.alarms:
            if self.ADapi.get_state(alarm, namespace = self.HASS_namespace) == 'on':
                return
        self.fire_active = False
        self.ADapi.fire_event(translations.MODE_CHANGE, mode = translations.false_alarm, namespace = self.HASS_namespace)
