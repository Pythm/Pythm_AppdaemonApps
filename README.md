# Pythm's Appdaemon Apps

I have created a script to clone and pull my repositories. The discussion can be found here: [How to keep repositories up to date.](https://github.com/Pythm/Pythm_AppdaemonApps/discussions/1)

To suppress the errors for files not associated with a configuration you can define `missing_app_warnings` to 0 in your appdaemon.yaml file. [Check out Appdaemon readme](https://appdaemon.readthedocs.io/en/latest/CONFIGURE.html#appdaemon)

## Usage
Configure automations with .yaml files in your conf/apps folder.

## Configuration of different apps
The 'notify_mobiles.py' is the standard app for notifying using my apps. It's name defaults to 'notify_mobiles' If you call it something else you need to configure other apps with 'notify_app' and name of the app, to get notifications. Failing to either use standard name or configure with other name will result in an error.

### appliance_notify

```yaml
tumbledryer:
  module: appliance_notify
  class: Dryer
  notify_reciever:
    - Me
    - Mykid
  notify_title: 'Tumbledryer'
  notify_message: 'Tumbledryer is finished'
  dryer_switch: switch.bod_stikk_tumbledryer
  dryer_power: sensor.bod_stikk_tumbledryer_power
```

### bathroomWindow

```yaml
window_bath:
  module: bathroomWindow
  class: BathroomWindow
  sensors:
    - sensor: binary_sensor.bad_vindu_contact
      duration: 1200
  humidity: sensor.bad_multisensor_humidity
  #refresh: True
  humidity_minimum: sensor.min_bath_humid
  check_below_temp: 20
  notify_reciever:
    - Me
    - Mywife
  notify_title: 'Window bath'
  notify_message: 'Humidity is down'

```

### change_dns_cloudflare

```yaml
update_cloudflare_dns:
  module: change_dns_cloudflare
  class: Change_DNS
  cloudflare_api_token: !secret cloudflare_api_token
  zone_id: cfced792412e54e171f33a2e95dXXXXX
  dns_record_id: 08e9fa448a8c0ce4d87445e5120XXXXX
  enable_proxy: False # Defaults to True if not configured
```

### door_guard

```yaml
frige:
  module: door_guard
  class: DoorGuard
  sensors:
    - sensor: binary_sensor.bod_fryseskap_window_door_is_open
      duration: 300
  notify_reciever:
    - Me
    - Mywife
    - Mykid
  notify_title: 'Fridgedoor'
  notify_message: 'Fridgedoor has been left open for 5 minutes'
```

### doorbell

```yaml
doorbell:
  module: doorbell
  class: Doorbell
  notify_reciever:
    - Me
    - Mykid
  notify_message: 'Someone at the door'
  doorbell: binary_sensor.front_door_ding
  camera: camera.front_door_live_view
  media_player:
    - media_player.appletv
```

### end_vacation

```yaml
vacation_end:
  module: end_vacation
  class: endVacation
  vacation_switch:
    - input_boolean.vacation
    - input_boolean.vacation_ac
  vacation_ends: input_datetime.end_vacation
  presence:
    - person.me
```

`presence` will turn off vacation when returning home.

### espresso_machine

```yaml
rancilio:
  module: espresso_machine
  class: EspressoMachine
  espresso_machine: switch.kitch_espresso
  coffee_timer: input_datetime.turn_on_coffee
  ios_toggle: espresso
  notify_reciever:
    - Me
  notify_title: 'Coffee'
  notify_message: 'Coffee machine is still on'
```

The notification setup will remind you if the coffee machine is still on at 15:00

### fire_alarm

```yaml
firealarm:
  module: fire_alarm
  class: FireAlarm
  notify_reciever:
    - Me
    - Email
  alarms:
    - binary_sensor.654_aaa_zone_1_smoke
    - binary_sensor.654_aaa_zone_2_smoke
  turn_off:
    - switch.dishwasher_power
    - switch.kitch_espresso
    - fan.mi_air_purifier
  screens:
    - cover.screen
    - cover.garage_door
```

### garagedoor

```yaml
garagecover:
  module: garagedoor
  class: GarageDoor
  garage: cover.garage_door
  auto_open:
    - input: input_boolean.auto_open_garage
      presence: person.me
  ios_open: openGarage
  ios_close: closeGarage
```

### media_stop

```yaml
stop_AppleTv:
  module: media_stop
  class: MediaStop
  sensors:
    - binary_sensor.front_door_ding
  mediaplayer:
    - media_player.loft
```

### notify_mobiles

```yaml
notify_mobiles:
  module: notify_mobiles
  class: Notify_Mobiles
  recipients:
    - person: Me
      reciever: 
        - mobile_app_my_phone
      tracker: person.me
    - person: Email
      reciever: 
        - gmail

  siri_message: 
    - message: food
      notify_reciever:
        - Me
      notify_title: 'Food'
      notify_message: 'Food is on the table!'
    - message: night # Just for calling night mode from ios event
      
  notify_state_change:
    - sensor: sensor.myip
      notify_title: 'New IP adresse'
      notify_message: 'New IP adresse is'
      notify_reciever:
        - Email
        - Me
```
Set up people and their devices with recipients. If tracker is provided it will not send notificatios if not home by default.

Siri messages or ios events will do a mode change event and also send notifications.

Notify state change will listen for state change and notify you

### rain_notify

```yaml
notify_on_rain:
  module: rain_notify
  class: Rain_Notify
  rain_sensor:
    - sensor.netatmo_regnsensor_rain
  rain_amount: 0.1
  anemometer:
    - sensor.netatmo_anemometer_wind_strength
  anemometer_speed: 20
  windowsensors:
    - binary_sensor.window_door_is_open
  notify_reciever:
    - Me
```

### simultaneousOpened

```yaml

window_and_door:
  module: simultaneousOpened
  class: SimultaneousOpen
  sensors:
    - sensor: binary_sensor.door_contact
      duration: 300
  simultaneous_sensor: binary_sensor.window_door_is_open
  temperature_sensor: sensor.stue_temperature_temperature
  check_below_temp: 22.4 # Only notify if temperature is below value
  notify_reciever:
    - Kid
  notify_title: 'Both door and window is open'
  notify_message: 'Close either'

```

### wake_up

```yaml

wake_up_alarm:
  module: wake_up
  class: WakeUp
  MQTT_namespace: mqtt
  
  workday: binary_sensor.workday_sensor
  vacation: input_boolean.vekk_reist
  alarm_switch: input_boolean.alarm_switch_nathaniel
  alarm_switch_non_work_day: input_boolean.alarm_switch_non_work_day_nathaniel

  media_player: media_player.nathaniel
  volume: 0.6
  playlist: Playlists/Morgen_Nathaniel
  
  wake_up_MQTTlights:
    - zigbee2mqtt/NATH_HueGradient
  light_data:
    brightness: 80
    effect: sunrise

  time: input_datetime.vekkeklokke_nathaniel
  light_time_offset: 5

  conditions:
    - "self.get_tracker_state('person.nathaniel') == 'home'"

```