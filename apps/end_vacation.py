""" Stop vacation mode at given time or tracker/presence change.

    # Changelog:
    0.1.2: Starts listening for person returning home two hours after vacation start.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.1.2"

from appdaemon.plugins.hass.hassapi import Hass


class endVacation(Hass):

    def initialize(self):
        if 'namespace' in self.args:
            self.set_namespace(self.args['namespace'])
        self.listen_handle = {}
        self.vacation_handle = None
        self.vacation_switch = self.args['vacation_switch']
        self.presence = self.args.get('presence', [])

        self.vacation_ends = self.args.get('vacation_ends', None)
        if self.vacation_ends:
            if self.datetime() < self.parse_datetime(self.get_state(self.vacation_ends)):
                self.vacation_handle = self.run_at(self.endVacation,
                    self.parse_datetime(self.get_state(self.vacation_ends))
                )
            self.listen_state(self.endVacationAt, self.vacation_ends, duration = 60)

        for switch in self.vacation_switch:
            if self.get_state(switch) == 'on':
                for person in self.presence:
                    person_handler = self.listen_state(self.presenceChange, person,
                        new = 'home'
                    )
                    self.listen_handle.update(
                        {person : person_handler}
                    )
            else: 
                self.listen_state(self.onVacation, switch,
                    new = 'on',
                    duration = 7200
                )

    def onVacation(self, entity, attribute, old, new, kwargs) -> None:
        """ Starts listening for presence change to end vacation when new state is home
        """
        for person in self.presence:
            person_handler = self.listen_state(self.presenceChange, person,
                new = 'home'
            )
            self.listen_handle.update(
                {person : person_handler}
            )

    def presenceChange(self, entity, attribute, old, new, kwargs) -> None:
        """ Listens for presence change and ends vacations if new state is home
        """
        self.endVacation(0)

    def endVacationAt(self, entity, attribute, old, new, kwargs) -> None:
        """ Updates time for when to end vacation
        """
        if self.datetime() < self.parse_datetime(self.get_state(self.vacation_ends)):
            if self.vacation_handle is not None:
                if self.timer_running(self.vacation_handle):
                    try:
                        self.cancel_timer(self.vacation_handle)
                    except Exception as e:
                        self.log(
                            f"Could not stop handler in {self.name} for {self.vacation_ends}. Exception {e}",
                            level = 'DEBUG'
                        )
            self.vacation_handle = self.run_at(self.endVacation, self.parse_datetime(self.get_state(self.vacation_ends)))

    def endVacation(self, kwargs) -> None:
        """ Ends vacation by turning off switch
        """
        for switch in self.vacation_switch:
            self.turn_off(switch)

        for person in self.presence:
            if self.listen_handle.get(person) is not None:
                try:
                    self.cancel_listen_state(self.listen_handle.get(person))
                except Exception as e:
                    self.log(
                        f"Could not stop handler in {self.name} for {entity}. Exception {e}",
                        level = 'DEBUG'
                    )

        if self.vacation_handle is not None:
            if self.timer_running(self.vacation_handle):
                try:
                    self.cancel_timer(self.vacation_handle)
                except Exception as e:
                    self.log(
                        f"Could not stop handler in {self.name} for {self.vacation_ends}. Exception {e}",
                        level = 'DEBUG'
                    )