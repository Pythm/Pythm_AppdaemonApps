""" Start appliances in Home Connect integration
    Electrical appliances like washing mashimes should only be used when awake. Use at own risk.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.0.1"

from appdaemon import adbase as ad
import datetime

class HomeConnect(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.electricalPrice = self.ADapi.get_app('electricalPriceCalc')
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        self.notify_reciever = self.args['notify_reciever']

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        if 'vacation' in self.args:
            self.vacation = self.args['vacation']
        else:
            self.vacation = 'input_boolean.vacation'
            if not self.ADapi.entity_exists(self.vacation, namespace = self.HASS_namespace):
                self.ADapi.call_service("state/set",
                    entity_id = self.vacation,
                    attributes = {'friendly_name' : 'Vacation'},
                    state = 'off',
                    namespace = self.HASS_namespace
                )
            else:
                self.ADapi.log(
                    "'vacation' not configured. Using 'input_boolean.vacation' as default away state",
                    level = 'INFO'
                )

        self.remote_start = self.args['remote_start']
        self.active_program = self.args['active_program']
        if 'night' in self.args:
            self.nightprogram = self.args['night']
        else:
            self.nightprogram = None
            self.ADapi.log(
                f"Night program not configured for {self.ADapi.get_state(remote_start, attribute='friendly_name')}.",
                level = 'INFO'
            )
        if 'day' in self.args:
            self.dayprogram = self.args['day']
        else:
            self.dayprogram = None
            self.ADapi.log(
                f"Day program not configured for {self.ADapi.get_state(remote_start, attribute='friendly_name')}.",
                level = 'INFO'
            )

        self.handler = None

            # Vacation setup
        self.away_state = self.ADapi.get_state(self.vacation, namespace = self.HASS_namespace)  == 'on'
        self.ADapi.listen_state(self.awayStateListen, self.vacation,
            namespace = self.HASS_namespace
        )
            # Program setup
        if not 'running_time' in self.nightprogram:
            self.nightprogram.update(
                {'running_time': 4}
            )
        if not 'running_time' in self.dayprogram:
            self.dayprogram.update(
                {'running_time': 4}
            )
        self.ADapi.listen_state(self.remoteStartRequested, self.remote_start,
            new = 'on',
            namespace = self.HASS_namespace
        )

        if (
            self.ADapi.get_state(self.remote_start, namespace = self.HASS_namespace) == 'on'
            and not self.away_state
        ):
            self.ADapi.run_in(self._findTimeForWashing,70)

        self.dayruntime = self.ADapi.parse_datetime('07:00:00') - datetime.timedelta(hours=int(self.nightprogram['running_time']))
        self.dayruntime_stop = self.ADapi.parse_datetime('16:00:00') - datetime.timedelta(hours=int(self.dayprogram['running_time']))

    def remoteStartRequested(self, entity, attribute, old, new, kwargs) -> None:
        """ Remote start signal received.
        """
        self._findTimeForWashing(0)


    def _findTimeForWashing(self, kwargs) -> None:
        """ Finds cheapest time to run appliance.
        """
        if self.ADapi.now_is_between(str(self.dayruntime.time()), str(self.dayruntime_stop.time())):
            # Run during daytime
            startWashingAt, EndAt, price = self.electricalPrice.get_Continuous_Cheapest_Time(
                hoursTotal = self.dayprogram['running_time'],
                calculateBeforeNextDayPrices = True,
                finishByHour = 16
            )

            if startWashingAt is not None:
                if startWashingAt > self.ADapi.datetime(aware=True):
                    self.resetHandler()
                    self.handler = self.ADapi.run_at(self.startWashing, startWashingAt,
                        program = self.dayprogram['program']
                    )
                    self.notify_app.send_notification(
                        message = f"Starting {self.dayprogram['program']} "
                        f"at {startWashingAt}",
                        message_title = "Appliances",
                        message_recipient = self.notify_reciever,
                        also_if_not_home = False
                    )
                    return
        else:
            # Run during nighttime
            startWashingAt, EndAt, price = self.electricalPrice.get_Continuous_Cheapest_Time(
                hoursTotal = self.nightprogram['running_time'],
                calculateBeforeNextDayPrices = False,
                finishByHour = 8
            )

            if startWashingAt is not None:
                if startWashingAt > self.ADapi.datetime(aware=True):
                    self.resetHandler()
                    self.handler = self.ADapi.run_at(self.startWashing, startWashingAt,
                        program = self.nightprogram['program']
                    )
                    self.notify_app.send_notification(
                        message = f"Starting {self.nightprogram['program']} "
                        f"at {startWashingAt}",
                        message_title = "Appliances",
                        message_recipient = self.notify_reciever,
                        also_if_not_home = False
                    )
                    return

        self.ADapi.run_in(self.startWashing, 10,
            program = self.nightprogram['program']
        )

    def startWashing(self, **kwargs) -> None:
        """ Starts appliance
        """
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

    def resetHandler(self) -> None:
        """ Resets handler for appliance before setting up a new runtime.
        """
        if self.handler != None:
            if self.ADapi.timer_running(self.handler):
                try:
                    self.ADapi.cancel_timer(self.handler)
                except Exception as e:
                    self.ADapi.log(f"Not possible to stop timer for appliance. {e}", level = 'DEBUG')
            self.handler = None

    def awayStateListen(self, entity, attribute, old, new, kwargs) -> None:
        """ Listen for changes in vacation switch to prevent application to start when on vacation.
        """
        self.away_state = new == 'on'

