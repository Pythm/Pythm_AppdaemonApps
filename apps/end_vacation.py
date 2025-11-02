""" Stop vacation mode at given time or tracker/presence change.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.2.1"

from appdaemon import adbase as ad

class endVacation(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.listen_handle = {}
        self.vacation_handle = None
        self.vacation_switch = self.args['vacation_switch']
        self.presence = self.args.get('presence', [])

        self.vacation_ends = self.args.get('vacation_ends', None)
        if self.vacation_ends:
            try:
                vacation_end_time = self.ADapi.get_state(self.vacation_ends,
                                                         namespace = self.HASS_namespace)
            except TypeError:
                self.ADapi.log(
                    f"TypeError setting vacation ending for {self.name}. Error: {t}",
                    level='INFO')
                pass
            else:
                if self.ADapi.datetime(aware=True) < self.ADapi.parse_datetime(vacation_end_time, aware=True):
                    self.vacation_handle = self.ADapi.run_at(self.endVacation,
                                                            vacation_end_time,
                                                            namespace = self.HASS_namespace)
            self.ADapi.listen_state(self._endVacationAt,
                                    self.vacation_ends,
                                    duration = 60,
                                    namespace = self.HASS_namespace)

        for switch in self.vacation_switch:
            if self.ADapi.get_state(switch, namespace = self.HASS_namespace) == 'on':
                self._create_listen_for_return_home()
            else: 
                self.ADapi.listen_state(self._onVacation,
                                        switch,
                                        new = 'on',
                                        duration = 7200,
                                        namespace = self.HASS_namespace)

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
        self.endVacation(0)

    def _endVacationAt(self, entity, attribute, old, new, kwargs) -> None:
        try:
            vacation_end_time = self.ADapi.get_state(self.vacation_ends,
                                                     namespace = self.HASS_namespace)
        except TypeError as t:
            self.ADapi.log(
                f"TypeError setting vacation ending for {self.name}. Error: {t}",
                level='INFO')
            return
        if self.ADapi.datetime(aware=True) < self.ADapi.parse_datetime(vacation_end_time, aware=True):
            self._cancel_vacation_handle()
            self.vacation_handle = self.ADapi.run_at(self.endVacation, vacation_end_time)

    def endVacation(self, kwargs) -> None:
        """ Ends vacation by turning off switch
        """
        for switch in self.vacation_switch:
            self.ADapi.call_service('input_boolean/turn_off',
                entity_id = switch,
                namespace = self.HASS_namespace
            )
        self._cancel_listen_handlers()
        self._cancel_vacation_handle()

    def _cancel_listen_handlers(self):
        for person in self.presence:
            if self.listen_handle.get(person) is not None:
                try:
                    self.ADapi.cancel_listen_state(self.listen_handle.get(person))
                except Exception as e:
                    self.ADapi.log(
                        f"Could not stop handler in {self.name} for {person}. Exception {e}",
                        level = 'DEBUG'
                    )

    def _cancel_vacation_handle(self):
        if self.vacation_handle is not None:
            if self.ADapi.timer_running(self.vacation_handle):
                try:
                    self.ADapi.cancel_timer(self.vacation_handle)
                except Exception as e:
                    self.ADapi.log(
                        f"Could not stop handler in {self.name} for {self.vacation_ends}. Exception {e}",
                        level = 'DEBUG'
                    )