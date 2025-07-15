""" Notify when it starts to rain or if it is windy and windows are open

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.2"

from appdaemon import adbase as ad

class Rain_Notify(ad.ADBase):

    def initialize(self):

        self.ADapi = self.get_ad_api()
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        self.notify_reciever = self.args['notify_reciever']

            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')

        self.windowsensors = self.args['windowsensors']

        self.windows_needed_to_be_closed = []
        self.push_notice = True

        self.rain_amount:float = self.args.get('rain_amount', 0.1)

        self.anemometer_speed:float = self.args.get('anemometer_speed',40)

        self.ADapi.listen_event(self.weather_event, 'WEATHER_CHANGE',
            namespace = self.HASS_namespace
        )

    def weather_event(self, event_name, data, kwargs) -> None:
        """ Listens for weather change from the weather app
        """
        if (
            data['rain'] >= self.rain_amount
            and self.windowsopened() > 0
            and self.push_notice
        ):
            self.notify_app.send_notification(
                message = f"It's raining and {self.windows_needed_to_be_closed} is open",
                message_title = "Rain",
                message_recipient = self.notify_reciever,
                also_if_not_home = False
            )
            self.push_notice = False
            self.ADapi.run_in(self.resetNotify, 10800)

        if (
            data['wind'] >= self.anemometer_speed
            and self.windowsopened() > 0
            and self.push_notice
        ):
            self.notify_app.send_notification(
                message = f"It's windy and {self.windows_needed_to_be_closed} is open",
                message_title = "Wind",
                message_recipient = self.notify_reciever,
                also_if_not_home = False
            )
            self.push_notice = False
            self.ADapi.run_in(self.resetNotify, 10800)

    def windowsopened(self) -> int:
        """ Returns number of opened windows and creates a list of those open.
        """
        opened = 0
        self.windows_needed_to_be_closed = []
        for window in self.windowsensors:
            if self.ADapi.get_state(window, namespace = self.HASS_namespace) == 'on':
                self.windows_needed_to_be_closed.append(
                    f"{self.ADapi.get_state(window, attribute = 'friendly_name', namespace = self.HASS_namespace)} "
                )
                opened += 1
        return opened

    def resetNotify(self, kwargs) -> None:
        """ Reset the timeout to send notification again.
        """
        self.push_notice = True