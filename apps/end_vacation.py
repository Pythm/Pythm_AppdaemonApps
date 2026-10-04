""" Stop vacation mode at given time or tracker/presence change.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.2.1"

from appdaemon import adbase as ad

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
        self.vacation_switch = _as_list(self.args['vacation_switch'])
        self.presence = _as_list(self.args.get('presence', []))
        # Seconds a vacation switch has to be on before a person arriving home ends the vacation
        self.arm_delay = int(self.args.get('arm_delay', 7200))

        self.vacation_ends = self.args.get('vacation_ends', None)
        if self.vacation_ends:
            self._schedule_end(self.ADapi.get_state(self.vacation_ends, namespace = self.HASS_namespace))
            self.ADapi.listen_state(self._endVacationAt,
                                    self.vacation_ends,
                                    duration = 60,
                                    namespace = self.HASS_namespace)

        vacation_is_on = False
        for switch in self.vacation_switch:
            state = self.ADapi.get_state(switch, namespace = self.HASS_namespace)
            if state is None:
                self.ADapi.log(f"{self.name}: vacation_switch {switch} was not found.", level = 'WARNING')
            vacation_is_on = vacation_is_on or state == 'on'
            # Also when the switch is on now, so the next vacation is armed as well
            self.ADapi.listen_state(self._onVacation,
                                    switch,
                                    new = 'on',
                                    duration = self.arm_delay,
                                    namespace = self.HASS_namespace)
        if vacation_is_on:
            self._create_listen_for_return_home()

    def _onVacation(self, entity, attribute, old, new, kwargs) -> None:
        self._create_listen_for_return_home()

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

    def _cancel_listen_handlers(self):
        for handler in self.listen_handle.values():
            if handler is not None:
                self.ADapi.cancel_listen_state(handler, silent = True)
        self.listen_handle = {}

    def _cancel_vacation_handle(self):
        if self.vacation_handle is not None:
            self.ADapi.cancel_timer(self.vacation_handle, silent = True)
            self.vacation_handle = None
