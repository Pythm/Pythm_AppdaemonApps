# 📦 Pythm's AppDaemon Apps
Welcome to Pythm's collection of **AppDaemon apps** tailored for automation, energy management, and smart‑home integration. These apps are designed for **supporters** and are part of a private repository.

---

## 🚀 Getting Started

### 1. **Clone and Setup**
If you are not comfortable with using `git clone`, you can follow this [setup guide](https://github.com/Pythm/Pythm_AppdaemonApps/discussions/1). It will clone and keep your repositories up to date.  

### 2. **Suppress Warnings**
To avoid warnings for unused apps, set `missing_app_warnings: 0` in your `appdaemon.yaml` file.

---

## 📌 Common Configuration

### 🔔 Notifications  
All apps use the `notify_mobiles` app by default (named `notify_mobiles`). If you rename this app, configure other apps with the `notify_app` parameter and the new name. You can also configure my public apps with `notify_app: notify_mobiles` to get additional notification functionality.

My public apps with notification:
- [ad-ClimateCommander](https://github.com/Pythm/ad-ClimateCommander)
- [ad-ElectricalManagement](https://github.com/Pythm/ad-ElectricalManagement)
- [ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement)


> [!TIP]  
> Long press notification for options

### 🧭 Namespace Configuration  
AppDaemon supports custom namespaces for Home Assistant and MQTT. If not configured, defaults are:

- **Home Assistant**: `default`  
- **MQTT**: `mqtt`  

Configure with:  

```yaml
HASS_namespace: default
MQTT_namespace: mqtt
```

### 🧭 Vacation settings

The default vacation helper from Home assistant is `input_boolean.vacation` in all my apps, please configure with
```yaml
  vacation: input_boolean.vacation
```
in the apps that relies on setting a vacation mode.


---

## 📦 App List  
Below are the available apps with configuration examples and requirements.  
**Most sensors that are not critical to the app’s functionality are optional.** Values given below are defaults.  

---

### 🧊 `appliance_home_connect`

**Function**: Starts appliances (e.g., dishwasher) when electricity prices are low.
**Requirements**:
  - [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc)
  - Notify app
**Note**: Electrical appliances like washing machines should only be used when awake. Use at your own risk.
**Controls**: Home Connect appliances. Could work on other appliances where you "select.select_option" to start.

**Description**
The program must be able to finish by 16:00 to run the day program, if not it will find time and finish before 8 in the morning.
Sends notification about scheduled time, with options to run program now.
Active vacation switch prevents machine from running and starts the machine when vacation is turned off.

**Example configuration**

```yaml
dishwasher:
  module: appliance_home_connect
  class: HomeConnect
  dependencies:
    - electricalPriceCalc
    - notify_mobiles
  vacation: input_boolean.vacation
  notify_receiver:
    - Me
  remote_start: binary_sensor.dishwasher_remote_start
  day:
    program: dishcare_dishwasher_program_eco_50
    running_time: 3 # In hours
  night:
    program: dishcare_dishwasher_program_night_wash
    running_time: 4 # In hours
```

---

### 🧺 `appliance_notify`

**Function**: Notifies when an appliance finishes (based on power sensor). If it finishes during the time window defined by turn_off_after and turn_off_before, the app automatically turns off the switch (if defined) to prevent beeping noises (e.g., from a tumble dryer).
Option from notifcation to turn off the switch.
After 60 seconds the switch is turned back on. Leaving the machine ready without any manual interference.

**Example configuration**

```yaml
tumbledryer:
  module: appliance_notify
  class: Dryer
  dependencies:
    - notify_mobiles
  notify_receiver:
    - Me
    - Mykid
  notify_title: 'Tumbledryer'
  notify_message: 'Tumbledryer is finished'
  dryer_switch: switch.tumbledryer 
  turn_off_after: '22:00:00'
  turn_off_before: '07:00:00'
  dryer_power: sensor.tumbledryer_power
```

---

### 🚪 `bathroomWindow`  

**Function**: Notifies when bathroom humidity drops and window is open.  
**Requirements**: [ad-Weather](https://github.com/Pythm/ad-Weather)  

**Example configuration**

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
  offset: 5
  check_below_temp: 20
  notify_receiver:
    - Me
    - Mywife
  notify_title: 'Bathroom Window Open'
  notify_message: 'Humidity is down to normal'
```

---

### 🌐 `change_dns_cloudflare`

**Function**: Updates Cloudflare DNS with your public IP.  

**Setup Instructions**:  

- **cloudflare_api_token**: Generate one at your profile → **Authentications**. Use the **Edit Zone DNS** template.  
- **zone_id**: Found at the **Overview page** on [dash.cloudflare.com](https://dash.cloudflare.com).  
- **dns_record_id**: Use the **List DNS Records** API call to find it:  
  [https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records](https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records)  

Will listen to changes in Home Assistant DNS IP integration if `ip_sensor` is configured. If not it will check against `api.ipify.org` every hour, and on initialise.  

**Example configuration**

```yaml
update_cloudflare_dns:
  module: change_dns_cloudflare
  class: Change_DNS
  cloudflare_api_token: !secret cloudflare_api_token
  zone_id: !secret yourCloudflareZoneID
  dns_record_id: yourCloudflareZoneID
  enable_proxy: True
```

---

### 🔐 `door_guard`

**Function**: Notifies if a door/window is left open for a specified duration. Useful for fridges.  

**Example configuration**

```yaml
fridge:
  module: door_guard
  class: DoorGuard
  dependencies:
    - notify_mobiles
  sensors:
    - sensor: binary_sensor.window_door_is_open
      duration: 300
  notify_receiver:
    - Me
    - Mywife
    - Mykid
  notify_title: 'Name Your Door/Window'
  notify_message: 'Your notification'
```

---

### 🎵 `doorbell`

**Function**: Captures snapshots, sends notifications, and plays a video stream on active media players on sensor activation.

**Example configuration**

```yaml
doorbell:
  module: doorbell
  class: Doorbell
  target_directory: '/var/lib/docker/volumes/hass_config/_data/www/doorbell/'
  local_directory: '/local/doorbell/'
  dependencies:
    - notify_mobiles
  notify_receiver:
    - Me
    - Mykid
  doorbell: binary_sensor.front_door_ding
  chime: number.smart_poe_chime_volume
  daytime_volume: 80
  daytime_start: 06:00:00
  nighttime_volume: 30
  daytime_stop: 22:00:00

  camera: camera.front_door_live_view
  media_player:
    - media_player.NotAn_appleTV
  notify_message: 'Someone at the door'
  notify_when_away: True
```

---

### 🚪 `end_vacation`

**Function**: Automatically ends vacation mode on presence or datetime.  

**Example configuration**

```yaml
vacation_end:
  module: end_vacation
  class: endVacation
  vacation_switch:
    - input_boolean.vacation
    - input_boolean.vacation_ac
  presence:
    - person.me
  vacation_ends: input_datetime.vacation_ending
```

---

### ☕ `espresso_machine`

**Function**: Notifies if the coffee machine is still on at 15:00.

**iOS Toggle**:  
- Add an iOS toggle to manually turn the machine on/off from your iPhone or iWatch.
- Use an `input_datetime` to specify the time when the coffee machine should automatically turn on.  
  Set the time to `00:00:00` to disable this automatic start.  

**Example configuration**

```yaml
rancilio:
  module: espresso_machine
  class: EspressoMachine
  dependencies:
    - notify_mobiles
  espresso_machine: switch.kitch_espresso
  coffee_timer: input_datetime.espresso
  ios_toggle: espresso
  notify_receiver:
    - Me
  notify_title: 'Coffee'
  notify_message: 'Coffee machine is still on'
```

---

### 🔥 `fire_alarm`

**Requirements**: [ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement)  
**Function**: Integrates with fire alarms, mode management, and device control.  

**Example configuration**

```yaml
firealarm:
  module: fire_alarm
  class: FireAlarm
  modeManagementApp: manageModes
  dependencies:
    - manageModes
    - notify_mobiles
  notify_receiver:
    - Me
    - Email
  alarms:
    - binary_sensor.zone_1_smoke
  turn_off:
    - switch.dishwasher_power
    - switch.kitch_espresso
    - fan.mi_air_purifier
  screens:
    - cover.screen
    - cover.garage_door
```

---

### 🚗 `garagedoor`

**Function**: Opens/closes garage doors via iOS, and auto‑opens on presence.  

**Example configuration**

```yaml
garagecover:
  module: garagedoor
  class: GarageDoor
  target_directory: '/var/lib/docker/volumes/hass_config/_data/www/doorbell/'
  local_directory: '/local/doorbell/'
  dependencies:
    - notify_mobiles
  garage: cover.garage_door
  auto_open:
    - input: input_boolean.auto_open_garage
      presence: person.me
  notify_receiver:
    - Me
  camera: camera.camera_garage
```

---

### 📊 `log_energy_usage`

**Requirements**: [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc)  
**Function**: Logs energy usage and calculates costs per month.  

**Special Features**:  

- The **"Total"** item calculates the **average price** and **total cost** for the month.  
- Input texts and **guest** usage can be configured:  
  - `input_text: input_text.cost_pr_month` (for apartments)  
  - `guestUse: input_boolean.easeelader_guest_charging` (for guest usage). Sends a notification on cost after.  

**Example configuration**

```yaml
log_energy_usage:
  module: log_energy_usage
  class: LogEnergyUsage
  dependencies:
    - electricalPriceCalc
    - notify_mobiles
  csv_folder_path: '/conf/db/'
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

---

### 🎵 `media_pause`

**Function**: Pauses media players when the associated sensor becomes inactive (e.g., when a presence sensor detects absence).

**Example configuration**

```yaml
pause_nathaniel_roon:
  module: media_pause
  class: MediaPause
  sensors:
    - binary_sensor.presence_sensor_rom
  media_player:
    - media_player.roon
  # Use AppDaemon's built-in constraints to define when the app runs
  constrain_start_time: "07:30:00"
  constrain_end_time: "20:00:00"
```

---

### 🚫 `media_stop`

**Function**: Stops media players when a sensor (e.g., doorbell) is triggered.  

**Example configuration**

```yaml
stop_AppleTv:
  module: media_stop
  class: MediaStop
  sensors:
    - binary_sensor.front_door_ding
  media_player:
    - media_player.appleTV
```

---

### 📱 `notify_mobiles`

**Function**: Central notification hub for all apps with more advanced functions.

**Special Features**:  

- **Siri Messages**: Send notifications to other family members when using Siri.(e.g., `siri_message: - message: food`) when also updating `MODE_CHANGE` used in Lightwand.
- **Notify State Change**: Get instant notification when a state change on a sensor.

#### Configure Siri Messages:

In additon to trigger scripts to change lightmode you can setup Shortcut on iOS to send "Fire Event" and then also automatically send notifications.

  1. Open the **Shortcuts** app on your iPhone.
  2. Create a new shortcut or edit an existing one.
  3. Tap **Add Action**.
  4. Search for **Home Assistant**.
  5. Select the action called **Fire Event**

  6. **Configure the Action:**
  * **Event Name:** Give this a specific name: `ios.lightwand-mode-change`. This applies to all your 'siri_message' instances.
  * **Event Data:** This contains 'message' and your message name in JSON format. 

  **Example for "Food":**
  * **Event Name:** `ios.lightwand-mode-change`
  * **Event Data:** `{"message": "food"}`

  **Example for "Movie":**
  * **Event Name:** `ios.lightwand-mode-change` (Keep the name the same!)
  * **Event Data:** `{"message": "movie"}`

**Example configuration**

```yaml
notify_mobiles:
  module: notify_mobiles
  class: Notify_Mobiles
  recipients:
    - person: Me
      receiver: 
        - mobile_app_my_phone
      tracker: person.me
    - person: MyKids
      receiver:
        - mobile_app_my_first_kid
        - mobile_app_my_second_kid
    - person: Email
      receiver: 
        - gmail
  siri_message: 
    - message: food
      notify_receiver:
        - MyKids
      notify_title: 'Food'
      notify_message: 'Food is on the table!'

  notify_state_change:
    - sensor: sensor.myip
      notify_title: 'New IP adresse'
      notify_message: 'New IP adresse is'
      notify_receiver:
        - Email
        - Me
```

---

### 🌧️ `rain_notify`

**Requirements**: [ad-Weather](https://github.com/Pythm/ad-Weather)  
**Function**: Notifies when rain or wind conditions are met if a sensor is on.  

**Example configuration**

```yaml
notify_on_rain:
  module: rain_notify
  class: Rain_Notify
  dependencies:
    - notify_mobiles
  rain_sensor:
    - sensor.rain_sensor
  rain_amount: 0.1
  anemometer_speed: 40
  windowsensors:
    - binary_sensor.window
  notify_receiver:
    - Me
``` 

---

### 🚪 `simultaneousOpened`

**Function**: Notifies if multiple sensors (e.g., door and window) are open simultaneously.  

**Example configuration**

```yaml
window_and_door:
  module: simultaneousOpened
  class: SimultaneousOpen
  sensors:
    - sensor: binary_sensor.door_contact
      duration: 300
  simultaneous_sensor: binary_sensor.window_door_is_open
  temperature_sensor: sensor.temperature
  check_below_temp: 23 # Only notify if temperature is below value
  notify_receiver:
    - Kid
  notify_title: 'Both door and window is open'
  notify_message: 'Close either'
```

---

### 🕒 `wake_up`

**Function**: Custom wake‑up alarm with lights, media, and conditions.  

**Example configuration**

```yaml
wake_up_alarm:
  module: wake_up
  class: WakeUp
  country_code: 'NO'
  vacation: input_boolean.vacation
  alarm_switch: input_boolean.alarm_switch_workday
  alarm_switch_non_work_day: input_boolean.alarm_switch_holidays
  media_player: media_player.bedroom
  volume: 0.2 # Will not adjust volume if not configured.
  playlist: Playlists/Morning
  wake_up_lights:
    - light.bedroom_light
  wake_up_MQTTlights:
    - zigbee2mqtt/HueGradient
  light_data:
    brightness: 80
    effect: sunrise
  time: input_datetime.wakeup
  light_time_offset: 5
  conditions:
    - "self.get_tracker_state('person.wife') == 'home'"
```

---

## 📝 Additional Notes

### Support  
For issues or questions, contact [Pythm via GitHub](https://github.com/Pythm).  

---

## 📌 License  
All apps are distributed under the **MIT License**. Use at your own risk.  
```

---
