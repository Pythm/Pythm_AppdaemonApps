""" Notify on drop in electricity usage (finished program) on Appliances

    Watches a power sensor. When the power has been above start_threshold for start_duration
    seconds the appliance is running, and when it has then been below stop_threshold for
    stop_duration seconds the program is finished and a notification is sent.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon import adbase as ad

class Dryer(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.notify_app is None:
            self.ADapi.log(
                f"{self.name}: Could not find app '{name_of_notify_app}'. Add it to 'dependencies'. Aborting setup",
                level = 'ERROR'
            )
            return
        self.notify_receiver = self.args['notify_receiver']
        self.notify_title = self.args.get('notify_title', 'Tumbledryer')
        self.notify_message = self.args.get('notify_message', 'Tumbledryer is finished')

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

            # Power thresholds (W) and how long (seconds) they have to hold
        self.start_threshold:float = float(self.args.get('start_threshold', 100))
        self.stop_threshold:float = float(self.args.get('stop_threshold', 15))
        self.start_duration:int = int(self.args.get('start_duration', 30))
        self.stop_duration:int = int(self.args.get('stop_duration', 30))

        self.dryer_switch = self.args.get('dryer_switch', None)
        self.turn_back_on_handler = None
        if self.dryer_switch is not None:
            self.turn_off_action:str = 'turn_off_' + str(self.dryer_switch)
            self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action",
                action = self.turn_off_action,
                namespace = self.HASS_namespace
            )
            self.auto_turn_off_after = self.args.get('turn_off_after', '22:00:00')
            self.auto_turn_off_before = self.args.get('turn_off_before', '07:00:00')
            self.turn_back_on_after:int = int(self.args.get('turn_back_on_after', 60))
        self.dryer_power = self.args['dryer_power']

        self.running:bool = False
        self.debounce_handler = None

        power = self.ADapi.get_state(self.dryer_power, namespace = self.HASS_namespace)
        if power is None:
            self.ADapi.log(f"{self.name}: dryer_power {self.dryer_power} was not found.", level = 'WARNING')
        self.ADapi.listen_state(self._power_changed, self.dryer_power,
            namespace = self.HASS_namespace
        )
        self._evaluate(power)

    def _power_changed(self, entity, attribute, old, new, kwargs) -> None:
        self._evaluate(new)

    def _evaluate(self, value) -> None:
        """ Starts or cancels the timer that confirms that the appliance started or finished.
            Every new reading is checked, so a sensor that changes often works as well. """

        try:
            watts = float(value)
        except (TypeError, ValueError):
            # unavailable or unknown. Do not notify on missing data.
            self._cancel_debounce()
            return

        if not self.running:
            if watts > self.start_threshold:
                self._start_debounce(self._dryer_is_running, self.start_duration)
            else:
                self._cancel_debounce()
        else:
            if watts < self.stop_threshold:
                self._start_debounce(self._dryer_is_stopping, self.stop_duration)
            else:
                self._cancel_debounce()

    def _start_debounce(self, callback, seconds:int) -> None:
        if self.debounce_handler is None:
            self.debounce_handler = self.ADapi.run_in(callback, seconds)

    def _cancel_debounce(self) -> None:
        if self.debounce_handler is not None:
            self.ADapi.cancel_timer(self.debounce_handler, silent = True)
            self.debounce_handler = None

    def _dryer_is_running(self, **kwargs) -> None:
        """ Power has been high long enough. Now waiting for it to fall again """

        self.debounce_handler = None
        self.running = True

    def _dryer_is_stopping(self, **kwargs) -> None:
        """ Power has been low long enough. Notifies that the program is finished """

        self.debounce_handler = None
        self.running = False
        data = {
            'tag' : str(self.name),
            }
        if self.dryer_switch is not None:
            data = {
                'tag' : str(self.dryer_switch),
                'actions' : [{ 'action' : self.turn_off_action, 'title' : 'Turn Off', 'destructive' : True, 'icon' : 'sfsymbols:stop.circle.fill' }]
                }

            if self.ADapi.now_is_between(self.auto_turn_off_after, self.auto_turn_off_before):
                self.turn_off_appliance()

        self.notify_app.send_notification(
            message = self.notify_message,
            message_title = self.notify_title,
            message_recipient = self.notify_receiver,
            also_if_not_home = True,
            data = data
        )

    def _notify_event(self, event_name, data, **kwargs) -> None:
        self.turn_off_appliance()

    def turn_off_appliance(self) -> None:
        self.ADapi.call_service('homeassistant/turn_off',
            entity_id = self.dryer_switch,
            namespace = self.HASS_namespace
        )
        if self.turn_back_on_after > 0:
            if self.turn_back_on_handler is not None:
                self.ADapi.cancel_timer(self.turn_back_on_handler, silent = True)
            self.turn_back_on_handler = self.ADapi.run_in(self.turn_back_on, self.turn_back_on_after)

    def turn_back_on(self, **kwargs) -> None:
        self.turn_back_on_handler = None
        self.ADapi.call_service('homeassistant/turn_on',
            entity_id = self.dryer_switch,
            namespace = self.HASS_namespace
        )
