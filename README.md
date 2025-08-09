# Pythm's Appdaemon Apps

I have created a script to clone and pull my repositories. The discussion can be found here: [How to keep repositories up to date.](https://github.com/Pythm/Pythm_AppdaemonApps/discussions/1)

To suppress the errors for files not associated with a configuration you can define `missing_app_warnings` to 0 in your appdaemon.yaml file. [Check out Appdaemon readme](https://appdaemon.readthedocs.io/en/latest/CONFIGURE.html#appdaemon)

## Usage
Configure automations with .yaml files in your conf/apps folder.

## Common for all apps

#### Notifications
The 'notify_mobiles.py' is the standard app for notifying using my apps. It's name defaults to 'notify_mobiles' in all apps. If you call it something else you need to configure other apps with 'notify_app' and name of the app, to get notifications. Failing to either use standard name or configure with other name will result in an error.

Configure the names in the app and use the names as receivers in configuration of other apps

#### Namespace
A key feature of Appdaemon is the ability to define custom namespaces. Visit the [Appdaemon documentation](https://appdaemon.readthedocs.io/en/latest/CONFIGURE.html#) for more information.

If you have not configured any namespace for your HASS plugin in your 'appdaemon.yaml' file, you can safely ignore namespaces. The default for HASS is 'default'. If you use MQTT you will need to set a namespace for that.

All apps are configurable to change namespace with:
```yaml HASS_namespace: default ```
and if mqtt is applicable:
```yaml MQTT_namespace: mqtt ```

In addition there are some apps that allow use of namespace on certain entities if they are in another namespace than defined with HASS_namespace / default.

## Configuration of different apps

### appliance_home_connect

Requirements:
- [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc)

To start Home Connect appliances when electricity price is low. Will finish by 16:00 if started daytime or 07:00 if started in the evening.
Note: Electrical appliances like washing mashimes should only be used when awake. Use at own risk.

Long press notification to turn on now, if calculated time does not fit your schedule.

```yaml
dishwasher:
  module: appliance_home_connect
  class: HomeConnect
  dependencies:
    - electricalPriceCalc
    - notify_mobiles
  vacation: input_boolean.vacation
  notify_reciever:
    - Me
  remote_start: binary_sensor.dishwasher_remote_start
  active_program: select.dishwasher_active_program
  day:
    program: dishcare_dishwasher_program_eco_50
    running_time: 3
  night:
    program: dishcare_dishwasher_program_night_wash
    running_time: 4
```

### appliance_notify

Listens on the power sensor for when consumption goes above 100 for 30 seconds and then falls again below 15 for 30 seconds.
Long press notification to turn off if dryer_switch is configured

```yaml
tumbledryer:
  module: appliance_notify
  class: Dryer
  dependencies:
    - notify_mobiles
  notify_reciever:
    - Me
    - Mykid
  notify_title: 'Tumbledryer'
  notify_message: 'Tumbledryer is finished'
  dryer_switch: switch.tumbledryer
  dryer_power: sensor.tumbledryer_power
```

### bathroomWindow

Requirements:
- [ad-Weather](https://github.com/Pythm/ad-Weather)

Notifies when humidity is down below average +10 and window/sensor is open/on. Long press notification to stop further notifications.
```yaml
window_bath:
  module: bathroomWindow
  class: BathroomWindow
  dependencies:
    - notify_mobiles
  sensors:
    - sensor: binary_sensor.bad_vindu_contact
      duration: 1200
  humidity: sensor.bad_multisensor_humidity
  check_below_temp: 20
  notify_reciever:
    - Me
    - Mywife
  notify_title: 'BathWindow'
  notify_message: 'Humidity is down to a normal level'

```

### change_dns_cloudflare

Finding your public IP address
Will listen to changes in Home Assistant DNS IP integration if `ip_sensor` is configured.
If not it will check against 'api.ipify.org' every hour, and on initialize.

Links, authorization and ID's needed to connect to API to update cloudflare DNS with new IP.
- cloudflare_api_token. Generate one at your profile - Authentications. Use the Edit Zone DNS template.
- zone_id is found at the overview page at dash.cloudflare.com
- dns_record_id is the ID for each DNS record for the zone. Use "List DNS Records" Api call to find them.
    https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records

```yaml
update_cloudflare_dns:
  module: change_dns_cloudflare
  class: Change_DNS
  cloudflare_api_token: !secret cloudflare_api_token
  zone_id: yourCloudflareZoneID
  dns_record_id: yourCloudflareZoneID
  enable_proxy: False # Defaults to True if not configured
```

### door_guard

Notifies if a sensor has been on for duration. Long press notification to stop further notifications.
```yaml
frige:
  module: door_guard
  class: DoorGuard
  dependencies:
    - notify_mobiles
  sensors:
    - sensor: binary_sensor.window_door_is_open
      duration: 300
  notify_reciever:
    - Me
    - Mywife
    - Mykid
  notify_title: 'Fridgedoor'
  notify_message: 'Fridgedoor has been left open for 5 minutes'
```

### doorbell

Stores snapshots in the directory = '/root/.homeassistant/www/doorbell/' and sends notifications. Can also pause active media players and play camera stream from the camera.

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

Automatic ending of vacation mode on presence or datetime. `presence` will turn off vacation when discovered at home.

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

### espresso_machine

The notification setup will remind you if the coffee machine is still on at 15:00. Long press notification to turn off

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


### fire_alarm

Configure translation from Lightwand modes with: `lightwand_language` for language and `language_file` for path. Configure [ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement) to get some basic away functionality like not opening screens/garagedoors when nobody is home.

```yaml
firealarm:
  module: fire_alarm
  class: FireAlarm
  modeManagementApp: manageModes
  dependencies:
    - manageModes
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

Opens and closes covers with ios actions (from iPhone / iWatch). Autoopens on returning home if HA input boolean is on.
Listens to same Mode Event as Lightwand/ ModeManagement and fire_alarm and checks if garagedoor is closed when away/night mode is called. Notifies with option to close. Add a camera to get a snapshot with notification.
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
  notify_reciever:
    - Me
  camera: camera.camera_garage
```

### log_energy_usage

Logs energy usage every Nordpool spotprice periode and calculates total every month with price and avg price for total.

```yaml
log_energy_usage:
  module: log_energy_usage
  class: LogEnergyUsage
  dependencies:
    - electricalPriceCalc
    - notify_mobiles
  csv_folder_path: '/conf/db/'
  notify_reciever:
    - Me
  items:
    - name: Total
      entity: sensor.last_meter_consumption_home
    - name: Appartment
      entity: sensor.appartment_electric_consumption_kwh
      input_text: input_text.cost_pr_month
      namespace_input_text: hass_appartment
    - name: Easee
      entity: sensor.leia_levetidsforbruk
      guestUse: input_boolean.easeelader_guest_charging
      namespace_guest: hass_main
```
The items contains a list of entities with consumption to track. `name` is your preffered ID. If `name` is 'Total' the app will calculate avg price when calculation total every month.

Options:
- input_text will write cost of consumption to a HA input_text. Configure `namespace_input_text` if the `input_text` is in another namespace e.g. appartment.
- guestUse: Use any sensor reporting 'on' and app will calculate price and notify cost after sensor has been turned off. 

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

  country_code: 'NO'
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