""" Notify on drop in electricity usage (finished program) on Appliances

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

from appdaemon.plugins.hass.hassapi import Hass

class Dryer(Hass):

    def initialize(self):
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.get_app(name_of_notify_app)
        self.notify_receiver = self.args['notify_receiver']
        self.notify_title = self.args.get('notify_title', 'Tumbledryer')
        self.notify_message = self.args.get('notify_message', 'Tumbledryer is finished')

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.dryer_switch = self.args.get('dryer_switch', None)
        if self.dryer_switch is not None:
            self.turn_off_action:str = 'turn_off_' + str(self.dryer_switch)
            self.listen_event(self._notify_event, "mobile_app_notification_action", namespace = self.HASS_namespace)
            self.auto_turn_off_after = self.args.get('turn_off_after', '22:00:00')
            self.auto_turn_off_before = self.args.get('turn_off_before', '07:00:00')
        self.dryer_power = self.args['dryer_power']

        self.start_listen_state()

    def _dryer_is_running(self, entity, attribute, old, new, kwargs):
        """ Reacts to powerconsumption and waiting for it to fall again """

        self.listen_state(self._dryer_is_stopping, self.dryer_power,
            constrain_state=lambda x: float(x) < 15,
            duration = 30,
            oneshot = True,
            namespace = self.HASS_namespace
        )

    def _dryer_is_stopping(self, entity, attribute, old, new, kwargs):
        """ Reacts to powerconsumption falling and notifies """

        data = {
            'tag' : str(self.name),
            }
        if self.dryer_switch is not None:
            data = {
                'tag' : str(self.dryer_switch),
                'actions' : [{ 'action' : self.turn_off_action, 'title' : 'Turn Off', 'destructive' : True, 'icon' : 'sfsymbols:stop.circle.fill' }]
                }

            if self.now_is_between(self.auto_turn_off_after, self.auto_turn_off_before):
                self.turn_off_appliance()

        self.notify_app.send_notification(
            message = self.notify_message,
            message_title = self.notify_title,
            message_recipient = self.notify_receiver,
            also_if_not_home = True,
            data = data
        )
        self.start_listen_state()

    def _notify_event(self, event_name, data, **kwargs) -> None:
        if data['action'] == self.turn_off_action:
            self.turn_off_appliance()

    def turn_off_appliance(self) -> None:
        self.call_service('switch/turn_off',
            entity_id = self.dryer_switch,
            namespace = self.HASS_namespace
        )
        self.run_in(self.turn_back_on, 60)
    
    def turn_back_on(self, kwargs) -> None:
        self.call_service('switch/turn_on',
            entity_id = self.dryer_switch,
            namespace = self.HASS_namespace
        )

    def start_listen_state(self) -> None:
        self.listen_state(self._dryer_is_running, self.dryer_power,
            constrain_state=lambda x: float(x) > 100,
            duration = 30,
            oneshot = True,
            namespace = self.HASS_namespace
        )