""" Notify when it starts to rain or if it is windy and windows are open

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon import adbase as ad

class Rain_Notify(ad.ADBase):

    def initialize(self):

        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.notify_app is None:
            self.ADapi.log(f"{self.name}: Could not find app '{name_of_notify_app}'. Add it to 'dependencies'. Aborting setup", level = 'ERROR')
            return
        self.notify_receiver = self.args['notify_receiver']
        self.also_if_not_home:bool = self.args.get('also_if_not_home', False)

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        windowsensors = self.args['windowsensors']
        if isinstance(windowsensors, str):
            windowsensors = [windowsensors]
        self.windowsensors:list = list(windowsensors)

        # Only one notification of any kind is sent every notify_interval seconds
        self.push_notice = True
        self.notify_interval:int = int(self.args.get('notify_interval', 10800))

        self.rain_amount:float = float(self.args.get('rain_amount', 0.1))

        self.anemometer_speed:float = float(self.args.get('anemometer_speed',40))

        self.lux_level = self.args.get('lux_level', None)
        if self.lux_level is not None:
            self.lux_level = float(self.lux_level)

        # {windows} is replaced with the names of the sensors that are on
        self.texts = {
            'rain' : (self.args.get('rain_title', 'Rain'), self.args.get('rain_message', "It's raining and {windows} is open")),
            'wind' : (self.args.get('wind_title', 'Wind'), self.args.get('wind_message', "It's windy and {windows} is open")),
            'lux' : (self.args.get('lux_title', 'Lux'), self.args.get('lux_message', "It's getting dark and {windows} needs attention")),
        }

        self.ADapi.listen_event(self.weather_event, 'WEATHER_CHANGE',
            namespace = self.HASS_namespace
        )

    def _number(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def weather_event(self, event_name, data, **kwargs) -> None:
        """ Listens for weather change from the weather app """

        if not self.push_notice:
            return

        rain = self._number(data.get('rain'))
        wind = self._number(data.get('wind'))
        lux = self._number(data.get('lux'))

        if rain is not None and rain >= self.rain_amount:
            reason = 'rain'
        elif wind is not None and wind >= self.anemometer_speed:
            reason = 'wind'
        elif self.lux_level is not None and lux is not None and lux < self.lux_level:
            reason = 'lux'
        else:
            return

        windows = self.windowsopened()
        if not windows:
            return

        title, message = self.texts[reason]
        self.notify_app.send_notification(
            message = message.replace('{windows}', ', '.join(windows)),
            message_title = title,
            message_recipient = self.notify_receiver,
            also_if_not_home = self.also_if_not_home
        )
        self.push_notice = False
        self.ADapi.run_in(self.resetNotify, self.notify_interval)

    def windowsopened(self) -> list:
        """ Returns the names of the sensors that are on (open) """

        opened = []
        for window in self.windowsensors:
            if self.ADapi.get_state(window, namespace = self.HASS_namespace) == 'on':
                name = self.ADapi.get_state(window, attribute = 'friendly_name', namespace = self.HASS_namespace)
                opened.append(str(name or window).strip())
        return opened

    def resetNotify(self, **kwargs) -> None:
        """ Reset the timeout to send notification again """

        self.push_notice = True
