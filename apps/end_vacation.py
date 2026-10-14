""" Stop vacation mode at given time or tracker/presence change.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.3.0"

from appdaemon import adbase as ad

# Seconds a vacation switch has to be on before a person arriving home ends the vacation
DEFAULT_ARM_DELAY = 86400

def _as_list(value) -> list:
    """ A single entity in the configuration is treated as a list of one. """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)

class endVacation(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()

        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.listen_handle = {}
        self.vacation_handle = None
        self.arm_timers = {}
        self.vacation_switch = _as_list(self.args['vacation_switch'])
        self.presence = _as_list(self.args.get('presence', []))
        self.arm_delay = int(self.args.get('arm_delay', DEFAULT_ARM_DELAY))

        self.vacation_ends = self.args.get('vacation_ends', None)
        if self.vacation_ends:
            self._schedule_end(self.ADapi.get_state(self.vacation_ends, namespace = self.HASS_namespace))
            self.ADapi.listen_state(self._endVacationAt,
                                    self.vacation_ends,
                                    duration = 60,
                                    namespace = self.HASS_namespace)

        for switch in self.vacation_switch:
            state = self.ADapi.get_state(switch, namespace = self.HASS_namespace)
            if state is None:
                self.ADapi.log(f"{self.name}: vacation_switch {switch} was not found.", level = 'WARNING')
            # Also when the switch is on now, so the next vacation is armed as well
            self.ADapi.listen_state(self._onVacation,
                                    switch,
                                    new = 'on',
                                    duration = self.arm_delay,
                                    namespace = self.HASS_namespace)
            self.ADapi.listen_state(self._offVacation,
                                    switch,
                                    new = 'off',
                                    namespace = self.HASS_namespace)
            if state == 'on':
                self._arm_after_restart(switch)

    def _onVacation(self, entity, attribute, old, new, kwargs) -> None:
        self._create_listen_for_return_home()

    def _offVacation(self, entity, attribute, old, new, kwargs) -> None:
        """ A switch turned off before the wait after a restart was over. """
        self._cancel_arm_timer(entity)

    def _arm_after_restart(self, switch) -> None:
        """ The switch was already on when the app started. Wait only for what is left of
            arm_delay, counted from when the switch last changed, so a restart or reload of
            the app does not shorten the wait. """
        seconds_left = self._seconds_left(switch)
        if seconds_left <= 0:
            self._create_listen_for_return_home()
            return
        self._cancel_arm_timer(switch)
        self.arm_timers[switch] = self.ADapi.run_in(self._armTimer, seconds_left, switch = switch)

    def _armTimer(self, **kwargs) -> None:
        self.arm_timers.pop(kwargs.get('switch'), None)
        self._create_listen_for_return_home()

    def _seconds_left(self, switch) -> float:
        """ Seconds left of arm_delay. The whole delay if Home Assistant gives no usable time. """
        changed = self.ADapi.get_state(switch, attribute = 'last_changed', namespace = self.HASS_namespace)
        try:
            elapsed = (self.ADapi.get_now() - self.ADapi.convert_utc(changed)).total_seconds()
        except (TypeError, ValueError, AttributeError, NotImplementedError):
            return self.arm_delay
        if elapsed < 0:
            return self.arm_delay
        return max(0, self.arm_delay - elapsed)

    def _create_listen_for_return_home(self):
        self._cancel_listen_handlers()
        for person in self.presence:
            person_handler = self.ADapi.listen_state(self._presenceChange,
                                                     person,
                                                     new = 'home',
                                                     namespace = self.HASS_namespace
            )
            self.listen_handle.update(
                {person : person_handler}
            )

    def _presenceChange(self, entity, attribute, old, new, kwargs) -> None:
        self.endVacation()

    def _endVacationAt(self, entity, attribute, old, new, kwargs) -> None:
        self._schedule_end(new)

    def _schedule_end(self, value) -> None:
        """ Plans the end of the vacation at the date and time in vacation_ends.
            A time in the past or a value that is not a time (unknown, unavailable) plans nothing. """

        self._cancel_vacation_handle()
        try:
            end_time = self.ADapi.parse_datetime(value, aware = True)
        except (TypeError, ValueError, NotImplementedError):
            if value not in (None, 'unknown', 'unavailable'):
                self.ADapi.log(f"{self.name}: vacation_ends '{value}' is not a date and time.", level = 'WARNING')
            return
        if end_time > self.ADapi.get_now():
            self.vacation_handle = self.ADapi.run_at(self.endVacation, end_time)

    def endVacation(self, **kwargs) -> None:
        for switch in self.vacation_switch:
            self.ADapi.call_service('homeassistant/turn_off',
                entity_id = switch,
                namespace = self.HASS_namespace
            )
        self._cancel_listen_handlers()
        self._cancel_vacation_handle()
        for switch in list(self.arm_timers):
            self._cancel_arm_timer(switch)

    def _cancel_arm_timer(self, switch) -> None:
        handle = self.arm_timers.pop(switch, None)
        if handle is not None:
            self.ADapi.cancel_timer(handle, silent = True)

    def _cancel_listen_handlers(self):
        for handler in self.listen_handle.values():
            if handler is not None:
                self.ADapi.cancel_listen_state(handler, silent = True)
        self.listen_handle = {}

    def _cancel_vacation_handle(self):
        if self.vacation_handle is not None:
            self.ADapi.cancel_timer(self.vacation_handle, silent = True)
            self.vacation_handle = None
