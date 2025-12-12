""" Start appliances in Home Connect integration
    Electrical appliances like washing mashimes should only be used when awake. Use at own risk.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.1"

from appdaemon import adbase as ad
import datetime

class HomeConnect(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.electricalPrice = self.ADapi.get_app('electricalPriceCalc')
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        self.notify_receiver = self.args['notify_receiver']

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        vacation = self.args.get('vacation', 'input_boolean.vacation')
        if self.ADapi.entity_exists(vacation, namespace=self.HASS_namespace):
            self.away_state = self.ADapi.get_state(vacation, namespace=self.HASS_namespace) == 'on'
            self.ADapi.listen_state(
                self._awayStateListen,
                vacation,
                namespace=self.HASS_namespace
            )
        else:
            self.away_state = False

            # Program setup
        self.remote_start = self.args['remote_start']
        self.active_program = self.args['active_program']
        if 'night' in self.args:
            self.nightprogram = self.args['night']
            if not 'running_time' in self.nightprogram:
                self.nightprogram.update(
                    {'running_time': 4}
                )
        else:
            self.nightprogram = None
            self.ADapi.log(
                f"Night program not configured for {self.ADapi.get_state(self.remote_start, attribute='friendly_name')}.",
                level = 'INFO'
            )
        if 'day' in self.args:
            self.dayprogram = self.args['day']
            if not 'running_time' in self.dayprogram:
                self.dayprogram.update(
                    {'running_time': 3}
                )
        elif self.nightprogram:
            self.dayprogram = self.nightprogram
        else:
            self.dayprogram = None
            self.ADapi.log(
                f"Day program not configured for {self.ADapi.get_state(self.remote_start, attribute='friendly_name')}.",
                level = 'INFO'
            )
        self.handler = None

        self.ADapi.listen_state(self._remoteStartRequested, self.remote_start,
            new = 'on',
            old = 'off',
            namespace = self.HASS_namespace
        )
        if (
            self.ADapi.get_state(self.remote_start, namespace = self.HASS_namespace) == 'on'
            and not self.away_state
        ):
            self.ADapi.run_in(self._findTimeForWashing,70)

        self.dayruntime = self.ADapi.parse_datetime('07:00:00') - datetime.timedelta(hours=int(self.nightprogram['running_time']))
        self.dayruntime_stop = self.ADapi.parse_datetime('16:00:00') - datetime.timedelta(hours=int(self.dayprogram['running_time']))

        self.turn_on_action_day:str = 'turn_on_now_' + str(self.dayprogram)
        self.turn_on_action_night:str = 'turn_on_now_' + str(self.nightprogram)
        self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action", namespace = self.HASS_namespace)

    def _remoteStartRequested(self, entity, attribute, old, new, kwargs) -> None:
        self._findTimeForWashing(0)

    def _findTimeForWashing(self, kwargs) -> None:
        data = {
                'tag' : str(self.remote_start),
                'actions' : [{ 'action' : self.turn_on_action_day, 'title' : 'Turn on dayprogram' },
                             { 'action' : self.turn_on_action_night, 'title' : 'Turn on nightprogram' } ]
                }
        if self.ADapi.now_is_between(str(self.dayruntime.time()), str(self.dayruntime_stop.time())):
            # Run during daytime
            startWashingAt, EndAt, price = self.electricalPrice.get_Continuous_Cheapest_Time(
                hoursTotal = self.dayprogram['running_time'],
                calculateBeforeNextDayPrices = True,
                finishByHour = 16
            )
            if startWashingAt is not None:
                if startWashingAt > self.ADapi.datetime(aware=True):
                    self._resetHandler()
                    self.handler = self.ADapi.run_at(self.startWashing, startWashingAt,
                        program = self.dayprogram['program']
                    )
                    self.notify_app.send_notification(
                        message = f"Starting {self.dayprogram['program']} "
                        f"at {startWashingAt}",
                        message_title = "Appliances",
                        message_recipient = self.notify_receiver,
                        also_if_not_home = False,
                        data = data
                    )
                    return
            self.ADapi.run_in(self.startWashing, 10,
                program = self.dayprogram['program']
            )
        else:
            # Run during nighttime
            startWashingAt, EndAt, price = self.electricalPrice.get_Continuous_Cheapest_Time(
                hoursTotal = self.nightprogram['running_time'],
                calculateBeforeNextDayPrices = False,
                finishByHour = 8
            )
            if startWashingAt is not None:
                if startWashingAt > self.ADapi.datetime(aware=True):
                    self._resetHandler()
                    self.handler = self.ADapi.run_at(self.startWashing, startWashingAt,
                        program = self.nightprogram['program']
                    )
                    self.notify_app.send_notification(
                        message = f"Starting {self.nightprogram['program']} "
                        f"at {startWashingAt}",
                        message_title = "Appliances",
                        message_recipient = self.notify_receiver,
                        also_if_not_home = False,
                        data = data
                    )
                    return
            self.ADapi.run_in(self.startWashing, 10,
                program = self.nightprogram['program']
            )

    def startWashing(self, **kwargs) -> None:
        """ Starts program on appliance """

        program = kwargs['program']
        if (
            self.ADapi.get_state(self.active_program, namespace = self.HASS_namespace) != program
            and self.ADapi.get_state(self.remote_start, namespace = self.HASS_namespace) == 'on'
            and not self.away_state
        ):
            self.ADapi.call_service("select/select_option",
                entity_id = self.active_program,
                option = program,
                namespace = self.HASS_namespace
            )

    def _resetHandler(self) -> None:
        if self.handler != None:
            if self.ADapi.timer_running(self.handler):
                try:
                    self.ADapi.cancel_timer(self.handler)
                except Exception as e:
                    self.ADapi.log(f"Not possible to stop timer for appliance. {e}", level = 'DEBUG')
            self.handler = None

    def _awayStateListen(self, entity, attribute, old, new, kwargs) -> None:
        self.away_state = new == 'on'

    def _notify_event(self, event_name, data, **kwargs) -> None:
        program = None

        match data['action']:
            case self.turn_on_action_day:
                program = self.dayprogram['program']
            case self.turn_on_action_night:
                program = self.nightprogram['program']

        if program is not None:
            self.ADapi.run_in(self.startWashing, 1,
                program=program
            )