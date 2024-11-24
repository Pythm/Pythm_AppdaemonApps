""" Notify when it starts to rain or if it is windy if windows are open

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.1"

import appdaemon.plugins.hass.hassapi as hass

class Rain_Notify(hass.Hass):

    def initialize(self):

        self.windows_needed_to_be_closed = []
        self.push_notice = True

        self.notify_app = self.get_app('notify_mobiles')
        self.notify_reciever = self.args['notify_reciever']

        self.windowsensors = self.args['windowsensors']

        self.rain_sensor = self.args.get('rain_sensor', None)
        self.rain_amount:float = self.args.get('rain_amount', 0.1)
        for sensor in self.rain_sensor :
            self.listen_state(self.check_if_windows_needs_to_be_closed_rain, sensor)

        self.anemometer = self.args.get('anemometer', None)
        self.anemometer_speed:float = self.args.get('anemometer_speed',20)
        for sensor in self.anemometer:
            self.listen_state(self.check_if_windows_needs_to_be_closed_wind, sensor)


    def windowsopened(self):
        opened = 0
        self.windows_needed_to_be_closed = []
        for window in self.windowsensors:
            if self.get_state(window) == 'on':
                self.windows_needed_to_be_closed.append(f"{self.get_state(window, attribute = 'friendly_name')} ")
                opened += 1
        return opened


    def check_if_windows_needs_to_be_closed_rain(self, entity, attribute, old, new, kwargs):
        try:
            rain_amount = float(new)
        except ValueError as ve:
            rain_amount = 0
            self.log(f"Not able to set Rain amount. ValueError: {ve}", level = 'DEBUG')
        except Exception as e:
            rain_amount = 0
            self.log(f"Not able to set Rain amount. Exception: {e}", level = 'INFO')

        if (
            rain_amount >= self.rain_amount
            and self.windowsopened() != 0
            and self.push_notice
        ):
            for r in self.notify_reciever:
                self.notify_app.send_notification(
                    message = f"It's raining and {self.windows_needed_to_be_closed} is open",
                    message_title = "Rain",
                    message_recipient = r
                )
            self.push_notice = False
            self.run_in(self.resetNotify, 10800)
    

    def check_if_windows_needs_to_be_closed_wind(self, entity, attribute, old, new, kwargs):
        try:
            wind_amount = float(new)
        except ValueError as ve:
            wind_amount = 0
            self.log(f"Not able to set Wind amount. Exception: {ve}", level = 'DEBUG')
        except Exception as e:
            wind_amount = 0
            self.log(f"Not able to set Wind amount. Exception: {e}", level = 'INFO')

        if (
            wind_amount >= self.anemometer_speed
            and self.windowsopened() != 0
            and self.push_notice
        ):
            for r in self.notify_reciever:
                self.notify_app.send_notification(
                    message = f"It's windy and {self.windows_needed_to_be_closed} is open",
                    message_title = "Wind",
                    message_recipient = r
                )
            self.push_notice = False
            self.run_in(self.resetNotify, 10800)


    def resetNotify(self, kwargs):
        self.push_notice = True