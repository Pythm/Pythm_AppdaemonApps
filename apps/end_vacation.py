""" Stop vacation mode at given time or precense change.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.1.0"

import appdaemon.plugins.hass.hassapi as hass


class endVacation(hass.Hass):

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
                self.vacation_handle = self.run_at(self.endVacation, self.parse_datetime(self.get_state(self.vacation_ends)))
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
                    new = 'on'
                )


    def presenceChange(self, entity, attribute, old, new, kwargs):
        self.run_in(self.endVacation, 1)


    def onVacation(self, entity, attribute, old, new, kwargs):
        for person in self.presence:
            person_handler = self.listen_state(self.presenceChange, person,
                new = 'home'
            )
            self.listen_handle.update(
                {person : person_handler}
            )


    def endVacationAt(self, entity, attribute, old, new, kwargs):
        if self.datetime() < self.parse_datetime(self.get_state(self.vacation_ends)):
            if self.vacation_handle != None:
                if self.timer_running(self.vacation_handle):
                    try:
                        self.cancel_timer(self.vacation_handle)
                    except Exception as e:
                        self.log(
                            f"Could not stop handler in {self.name} for {self.vacation_ends}. Exception {e}",
                            level = 'DEBUG'
                        )
            self.vacation_handle = self.run_at(self.endVacation, self.parse_datetime(self.get_state(self.vacation_ends)))


    def endVacation(self, kwargs):
        for switch in self.vacation_switch:
            self.turn_off(switch)

        for person in self.presence:
            if self.listen_handle.get(person) != None:
                try:
                    self.cancel_listen_state(self.listen_handle.get(person))
                except Exception as e:
                    self.log(
                        f"Could not stop handler in {self.name} for {entity}. Exception {e}",
                        level = 'DEBUG'
                    )

        if self.vacation_handle != None:
            if self.timer_running(self.vacation_handle):
                try:
                    self.cancel_timer(self.vacation_handle)
                except Exception as e:
                    self.log(
                        f"Could not stop handler in {self.name} for {self.vacation_ends}. Exception {e}",
                        level = 'DEBUG'
                    )
