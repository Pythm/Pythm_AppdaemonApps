""" FireAlarm
Trigger a mode change if fire alarm is triggered.
Turns off switches and opens screens/garagedoors

    @Pythm / https://github.com/Pythm

"""

__version__ = "0.1.1"

import appdaemon.plugins.hass.hassapi as hass

class FireAlarm(hass.Hass):

    def initialize(self):
        self.notify_app = self.get_app('notify_mobiles')
        self.notify_reciever = self.args['notify_reciever']

        alarms = self.args.get('alarms', [])
        for alarm in alarms:
            self.listen_state(self.alarmactivated, alarm)
        
        self.turn_off_items = self.args.get('turn_off', [])

        sensor_states = self.get_state(entity='sensor')
        for sensor_id, sensor_states in sensor_states.items():
            if 'media_player.' in sensor_id:
                if not sensor_id in self.turn_off_items:
                    self.turn_off_items.append(sensor_id)

        self.screens = self.args.get('screens', [])

    def alarmactivated(self, entity, attribute, old, new, kwargs) -> None:
        """ Reacts to on and off from smoke detectors and fire alarms
        """
        if new == 'on':
            self.fire_event("MODE_CHANGE", mode = 'fire')
            for item in self.turn_off_items:
                try:
                    if self.get_state(item) == 'on':
                        self.turn_off(item)
                except Exception as exc:
                    self.log(
                        f"Could not turn off {item} when fire alarm was trigered. Exception: {exc}",
                        level = 'INFO'
                    )

            for screen in self.screens:
                try:
                    if self.get_state(screen, attribute='current_position') != 100:
                        self.call_service('cover/open_cover', entity_id= screen)
                except Exception as exc:
                    self.log(
                        f"Could not open {screen} when fire alarm was trigered. Exception: {exc}",
                        level = 'INFO'
                    )

            for r in self.notify_reciever:
                self.notify_app.send_notification(
                    message = f"{entity} {new}",
                    message_title = "Smoke detected",
                    message_recipient = r
                )

        elif (
            new == 'off'
            and old == 'on'
        ):
            self.fire_event("MODE_CHANGE", mode = 'false_alarm')
