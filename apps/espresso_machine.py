""" Espresso machine

Turns on switch based on datetime input and checks if it is turned off at 15:00

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.3.0"

from appdaemon import adbase as ad
import datetime

class EspressoMachine(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.notify_app is None:
            # The machine is still turned on at the set time, but no reminder can be sent
            self.ADapi.log(f"{self.name}: Could not find app '{name_of_notify_app}'. No reminder will be sent. Add it to 'dependencies'.", level = 'ERROR')
        self.notify_receiver = self.args['notify_receiver']
        self.notify_title = self.args.get('notify_title', 'Coffee')
        self.notify_message = self.args.get('notify_message', 'Coffee machine is still on')

        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        vacation = self.args.get('vacation', 'input_boolean.vacation')
        vacation_state = self.ADapi.get_state(vacation, namespace=self.HASS_namespace)
        if vacation_state is not None:
            self.away_state = vacation_state == 'on'
            self.ADapi.listen_state(
                self._awayStateListen,
                vacation,
                namespace=self.HASS_namespace
            )
        else:
            self.away_state = False

        self.handler = None

        self.espresso_machine = self.args['espresso_machine']
        last_chance = self.args.get('last_chance', '15:00:00')
        self.ADapi.run_daily(self._check_coffee_machine_is_off, last_chance)

        if 'coffee_timer' in self.args:
            self.coffee_timer = self.args['coffee_timer']
            self.ADapi.listen_state(self._set_start_up_time, self.coffee_timer,
                duration = 5,
                namespace = self.HASS_namespace
            )
            self._schedule_start(self.ADapi.get_state(self.coffee_timer, namespace = self.HASS_namespace))

        self.turn_off_action:str = 'turn_off_' + str(self.espresso_machine)
        self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action",
            action = self.turn_off_action,
            namespace = self.HASS_namespace
        )

    def _schedule_start(self, timestring) -> None:
        """ Plans the daily start. 00:00:00 turns the start off.
            A value that is not a time (unknown, unavailable) leaves the plan as it was. """

        try:
            start_time = self.ADapi.parse_time(timestring)
        except (TypeError, ValueError, NotImplementedError):
            if timestring not in (None, 'unknown', 'unavailable'):
                self.ADapi.log(f"{self.name}: coffee_timer '{timestring}' is not a time.", level = 'WARNING')
            return

        if self.handler is not None:
            self.ADapi.cancel_timer(self.handler, silent = True)
            self.handler = None
        if start_time != datetime.time(0, 0, 0):
            self.handler = self.ADapi.run_daily(self._turn_on_coffee_machine, start_time)

    def _set_start_up_time(self, entity, attribute, old, new, kwargs) -> None:
        self._schedule_start(new)

    def _turn_on_coffee_machine(self, **kwargs) -> None:
        if self.ADapi.get_state(self.espresso_machine, namespace = self.HASS_namespace) == 'off' and not self.away_state:
            self.ADapi.call_service('homeassistant/turn_on',
                              entity_id = self.espresso_machine,
                              namespace = self.HASS_namespace)

    def _check_coffee_machine_is_off(self, **kwargs) -> None:
        if self.notify_app is None:
            return
        if self.ADapi.get_state(self.espresso_machine, namespace = self.HASS_namespace) == 'on':
            data = {
                'tag' : str(self.espresso_machine),
                'actions' : [{ 'action' : self.turn_off_action, 'title' : 'Turn Off', 'destructive' : True }]
                }
            self.notify_app.send_notification(
                message = self.notify_message,
                message_title = self.notify_title,
                message_recipient = self.notify_receiver,
                also_if_not_home = True,
                data = data
            )

    def _notify_event(self, event_name, data, **kwargs) -> None:
        if data.get('action') == self.turn_off_action:
            self.ADapi.call_service('homeassistant/turn_off',
                entity_id = self.espresso_machine,
                namespace = self.HASS_namespace
            )

    def _awayStateListen(self, entity, attribute, old, new, kwargs) -> None:
        self.away_state = new == 'on'
