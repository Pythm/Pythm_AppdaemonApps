""" Start appliances in Home Connect integration
    Electrical appliances like washing machines should only be used when awake. Use at own risk.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.3.0"

from appdaemon import adbase as ad
import datetime

from mode_names import translations

# How often and how many times a program is planned again when the price app has no answer yet.
PRICE_RETRY_SECONDS = 1800
PRICE_RETRY_MAX = 6

class HomeConnect(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        price_app_name = self.args.get('price_app', 'electricalPriceCalc')
        self.electricalPrice = self.ADapi.get_app(price_app_name)
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.electricalPrice is None or self.notify_app is None:
            self.ADapi.log(
                f"{self.name}: Could not find app '{price_app_name}' or '{name_of_notify_app}'. "
                "Add them to 'dependencies' in the configuration. Aborting setup",
                level = 'ERROR'
            )
            return
        self.notify_receiver = self.args['notify_receiver']

        vacation = self.args.get('vacation', 'input_boolean.vacation')
        vacation_state = self.ADapi.get_state(vacation, namespace = self.HASS_namespace)
        if vacation_state is not None:
            self.away_state = vacation_state == 'on'
            self.ADapi.listen_state(self._awayStateListen, vacation,
                namespace = self.HASS_namespace
            )
        else:
            self.away_state = False

        options = self.args.get('options', [])
        self.nightmode_calculate = 'run_during_nightmode' in options
        self.awaymode_calculate = 'run_during_awaymode' in options

            # Program setup
        self.remote_start = self.args['remote_start']
        self.active_program = self.args['active_program']

        self.nightprogram = self._load_program('night', running_time = 4, finish_by = 7)
        self.dayprogram = self._load_program('day', running_time = 3, finish_by = 16)
        if self.dayprogram is None and self.nightprogram is None:
            self.ADapi.log(
                f"{self.name}: No valid 'day' or 'night' program configured. Aborting setup",
                level = 'ERROR'
            )
            return
        if self.dayprogram is None:
            self.dayprogram = self.nightprogram
        if self.nightprogram is None:
            self.nightprogram = self.dayprogram

        self.handler = None

        self.ADapi.listen_state(self._remoteStartRequested, self.remote_start,
            new = 'on',
            namespace = self.HASS_namespace
        )

        # The day program is used between these times. Outside, the night program is used.
        self.dayruntime = self.ADapi.parse_datetime('00:00:00') + datetime.timedelta(hours=float(self.nightprogram['finish_by'])) - datetime.timedelta(hours=float(self.nightprogram['running_time']))
        self.dayruntime_stop = self.ADapi.parse_datetime('00:00:00') + datetime.timedelta(hours=float(self.dayprogram['finish_by'])) - datetime.timedelta(hours=float(self.dayprogram['running_time']))
        self.day_window_start:str = str(self.dayruntime.time())
        self.day_window_stop:str = str(self.dayruntime_stop.time())

        self.turn_on_action_day:str = f"turn_on_now_day_{self.remote_start}"
        self.turn_on_action_night:str = f"turn_on_now_night_{self.remote_start}"
        self.ADapi.listen_event(self._notify_event, "mobile_app_notification_action", namespace = self.HASS_namespace)

        # Listens for mode events
        self.lightmode = translations.automagical
        self.ADapi.listen_event(self.mode_event, translations.MODE_CHANGE, namespace = self.HASS_namespace)

    def _load_program(self, key:str, running_time:float, finish_by:float) -> dict | None:
        """ Returns a copy of the day or night program with defaults, or None if not configured/valid. """

        if key not in self.args:
            return None
        program = dict(self.args[key])
        if 'program' not in program:
            self.ADapi.log(f"{self.name}: '{key}' is missing the required 'program'. Ignoring '{key}'.", level = 'ERROR')
            return None
        program.setdefault('running_time', running_time)
        program.setdefault('finish_by', finish_by)
        return program

    def _remote_start_is_on(self) -> bool:
        return self.ADapi.get_state(self.remote_start, namespace = self.HASS_namespace) == 'on'

    # ------------------------------------------------------------------
    #  Remote start listener – only schedules if mode does not schedule
    # ------------------------------------------------------------------
    def _remoteStartRequested(self, entity, attribute, old, new, kwargs) -> None:
        """Trigger scheduling when a remote start is requested."""

        if self.ADapi.now_is_between(self.day_window_start, self.day_window_stop):
            if not self.awaymode_calculate or self.lightmode == translations.away:
                self._scheduleWashing(self.dayprogram)
        elif not self.nightmode_calculate or self.lightmode == translations.night:
            self._scheduleWashing(self.nightprogram)

    # ------------------------------------------------------------------
    #  Mode change listener – schedules immediately when the mode
    #  becomes active
    # ------------------------------------------------------------------
    def mode_event(self, event_name, data, **kwargs) -> None:
        """ Listens to mode events and reacts on night and away """

        mode = data.get('mode')
        # Only the modes of the whole house are tracked. Room modes, fire and free words
        # from iOS shortcuts are ignored, so they cannot hide that the house is in night mode.
        if mode == translations.reset:
            mode = translations.automagical
        if mode in (translations.automagical, translations.morning, translations.night, translations.away):
            self.lightmode = mode

        if not self._remote_start_is_on():
            return
        if mode == translations.away and self.awaymode_calculate:
            self._scheduleWashing(self.dayprogram)
        elif mode == translations.night and self.nightmode_calculate:
            self._scheduleWashing(self.nightprogram)

    # ------------------------------------------------------------------
    #  Away state listener – re‑schedule when we return home
    # ------------------------------------------------------------------
    def _awayStateListen(self, entity, attribute, old, new, kwargs) -> None:
        if new in ('unavailable', 'unknown'):
            return
        self.away_state = (new == 'on')
        if not self.away_state:
            self._scheduleWashing(self.dayprogram)

    # ------------------------------------------------------------------
    #  Centralised scheduling logic – calculates cheapest slot and
    #  schedules the dishwasher
    # ------------------------------------------------------------------
    def _scheduleWashing(self, program: dict, tries: int = 0) -> None:
        """Schedule the dishwasher using the cheapest time window.
            If the price app has no answer yet, it is asked again later (PRICE_RETRY_MAX times). """

        now = self.ADapi.get_now()
        before_next_day = program == self.dayprogram

        try:
            startWashingAt, _, _ = self.electricalPrice.get_Continuous_Cheapest_Time(
                hoursTotal = program['running_time'],
                calculateBeforeNextDayPrices = before_next_day,
                finishByHour = program['finish_by']
            )
        except Exception as e:
            self.ADapi.log(f"{self.name}: No price time for {program['program']}: {e}", level = 'WARNING')
            startWashingAt = None

        if startWashingAt is None:
            self._price_not_available(program, tries)
            return

        self._resetHandler()
        if startWashingAt > now:
            self.handler = self.ADapi.run_at(self.startWashing, startWashingAt,
                program = program['program']
            )
            self.notify_app.send_notification(
                message = f"Starting {program['program']} at {startWashingAt.strftime('%H:%M')}",
                message_title = "Appliances",
                message_recipient = self.notify_receiver,
                also_if_not_home = False,
                data = self._notification_data()
            )
        else:
            # The cheapest slot is now – run after a short delay
            self.handler = self.ADapi.run_in(self.startWashing, 10,
                program = program['program']
            )

    def _price_not_available(self, program: dict, tries: int) -> None:
        """ The price app has no start time yet (for example tomorrow's prices are not published). """

        self._resetHandler()
        if tries < PRICE_RETRY_MAX:
            self.handler = self.ADapi.run_in(self._retry_scheduling, PRICE_RETRY_SECONDS,
                program = program,
                tries = tries + 1
            )
            return
        self.ADapi.log(f"{self.name}: No price time found for {program['program']} after {tries} retries. Not started.", level = 'WARNING')
        self.notify_app.send_notification(
            message = f"Could not find a time to start {program['program']}. Not started. Use the buttons to start it now.",
            message_title = "Appliances",
            message_recipient = self.notify_receiver,
            also_if_not_home = False,
            data = self._notification_data()
        )

    def _retry_scheduling(self, **kwargs) -> None:
        self.handler = None
        if self._remote_start_is_on() and not self.away_state:
            self._scheduleWashing(kwargs['program'], kwargs['tries'])

    def _notification_data(self) -> dict:
        return {
            'tag': str(self.remote_start),
            'actions': [
                {'action': self.turn_on_action_day, 'title': 'Turn on dayprogram'},
                {'action': self.turn_on_action_night, 'title': 'Turn on nightprogram'}
            ]
        }

    def startWashing(self, **kwargs) -> None:
        """ Starts program on appliance """

        program = kwargs['program']
        if self.ADapi.get_state(self.active_program, namespace = self.HASS_namespace) == program:
            self.ADapi.log(f"{self.name}: {program} is already the active program. Not starting.", level = 'DEBUG')
        elif not self._remote_start_is_on():
            self.ADapi.log(f"{self.name}: Remote start is not on. Not starting {program}.", level = 'DEBUG')
        elif self.away_state:
            self.ADapi.log(f"{self.name}: Vacation is on. Not starting {program}.", level = 'DEBUG')
        else:
            self.ADapi.call_service("select/select_option",
                entity_id = self.active_program,
                option = program,
                namespace = self.HASS_namespace
            )

    def _resetHandler(self) -> None:
        if self.handler is not None:
            self.ADapi.cancel_timer(self.handler, silent = True)
            self.handler = None

    def _notify_event(self, event_name, data, **kwargs) -> None:
        action = data.get('action')
        if action == self.turn_on_action_day:
            program = self.dayprogram['program']
        elif action == self.turn_on_action_night:
            program = self.nightprogram['program']
        else:
            return

        self._resetHandler()
        self.handler = self.ADapi.run_in(self.startWashing, 1,
            program = program
        )
