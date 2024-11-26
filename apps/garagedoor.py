""" GarageDoor
Opening and closing of a cover entity

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

import appdaemon.plugins.hass.hassapi as hass

class GarageDoor(hass.Hass):

    def initialize(self):
        self.garagedoorHandler = None

        self.garage = self.args['garage']

        if 'ios_open' in self.args:
            self.ios_open = self.args['ios_open']
            self.listen_event(self.ios_open_garage, "ios.action_fired",
                actionName = self.ios_open
            )

        if 'ios_close' in self.args:
            self.ios_close = self.args['ios_close']
            self.listen_event(self.ios_close_garage, "ios.action_fired",
                actionName = self.ios_close
            )

        auto_open = self.args.get('auto_open', [])
        for ao in auto_open:
            self.listen_state(self.autoOpenGarage, ao['input'],
                auto_open = ao
            )
            if self.get_state(ao['input']) == 'on':
                self.garagedoorHandler = self.listen_state(
                    self.returningHome,
                    ao['presence'],
                    new = 'home',
                    auto_open = ao
                )


    def ios_open_garage(self, event_name, data, kwargs) -> None:
        """ Opens cover on ios event
        """
        self.call_service('cover/open_cover', entity_id= self.garage)


    def ios_close_garage(self, event_name, data, kwargs) -> None:
        """ Closes cover on ios event
        """
        self.call_service('cover/close_cover', entity_id= self.garage)


    def autoOpenGarage(self, entity, attribute, old, new, kwargs) -> None:
        """ Sets up a listener for when a tracker returns home to auto open garage
        """
        ao = kwargs['auto_open']
        if new == 'on':
            self.garagedoorHandler = self.listen_state(
                self.returningHome,
                ao['presence'],
                new = 'home',
                auto_open = ao
            )
        elif self.garagedoorHandler != None:
            try:
                self.cancel_listen_state(self.garagedoorHandler)
                self.garagedoorHandler = None
            except:
                self.log(
                    f"Ikke mulig å stoppe listen state for {self.garagedoorHandler} i Garagedoor",
                    level = 'DEBUG'
                )


    def returningHome(self, entity, attribute, old, new, kwargs) -> None:
        """ Auto open garage when tracker/person returns home
        """
        ao = kwargs['auto_open']
        if old != 'unavailable':
            self.call_service('cover/open_cover', entity_id= self.garage)
            self.turn_off(ao['input'])
            if self.garagedoorHandler != None:
                try:
                    self.cancel_listen_state(self.garagedoorHandler)
                    self.garagedoorHandler = None
                except:
                    self.log(
                    f"Ikke mulig å stoppe listen state for {self.garagedoorHandler} i Garagedoor",
                    level = 'DEBUG'
                )