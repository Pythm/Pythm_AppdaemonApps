# Pythm's Appdaemon Apps

Install with git clone:
With terminal cd into your Appdaemon apps folder. This should be something like: /docker/appdaemon/conf/apps
Git clone with: git clone https://github.com/Pythm/Pythm_AppdaemonApps.git

## Usage
Configure automations with .yaml files in your conf/apps folder.

## Configuration of different apps

### change_dns_cloudflare

```yaml
update_cloudflare_dns:
  module: change_dns_cloudflare
  class: Change_DNS
  log: info_log
  cloudflare_api_token: !secret cloudflare_api_token
  zone_id: cfced792412e54e171f33a2e95dXXXXX
  dns_record_id: 08e9fa448a8c0ce4d87445e5120XXXXX
  enable_proxy: False # Defaults to True if not configured
```

### end_vacation

```yaml
vacation_end:
  module: end_vacation
  class: endVacation
  log: info_log
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
  dependencies:
    - notify_mobiles
  log: info_log
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
  log: info_log
  notify_reciever:
    - Anders
    - Epost
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

### notify_mobiles

```yaml
notify_mobiles:
  module: notify_mobiles
  class: Notify_Mobiles
  log: info_log
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
  dependencies:
    - notify_mobiles
  log: info_log
  rain_sensor:
    - sensor.netatmo_regnsensor_rain
  rain_amount: 0.1
  anemometer:
    - sensor.netatmo_anemometer_wind_strength
  anemometer_speed: 20
  windowsensors:
    - binary_sensor.window_door_is_open
  notify_reciever:
    - Anders
```