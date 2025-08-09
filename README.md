# 📦 Pythm's AppDaemon Apps  

Welcome to Pythm's collection of **AppDaemon apps** tailored for automation, energy management, and smart home integration. These apps are designed for **paying customers** and are part of a private repository.  

---

## 🚀 Getting Started  

### 1. **Clone and Setup**  
Use the [setup guide](https://github.com/Pythm/Pythm_AppdaemonApps/discussions/1) to clone and keep your repositories up to date.  

### 2. **Suppress Warnings**  
To avoid warnings for unused apps, set `missing_app_warnings: 0` in your `appdaemon.yaml` file.  

---

## 📌 Common Configuration  

### 🔔 Notifications  
All apps use the `notify_mobiles.py` app by default (named `notify_mobiles`). If you rename this app, configure other apps with the `notify_app` parameter and the new name. You can also configure my public apps with `notify_app: notify_mobiles` to get some more options on notifications.

### 🧭 Namespace Configuration  
AppDaemon supports custom namespaces for HA and MQTT. If not configured, defaults are:  
- **HA**: `default`  
- **MQTT**: `mqtt`  

Configure with:  
```yaml
HASS_namespace: default
MQTT_namespace: mqtt
```

---

## 📦 App List  

Below are the available apps with configuration examples and requirements.  

---

### 🧊 `appliance_home_connect`  
**Requirements**: [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc)  
**Function**: Starts appliances (e.g., dishwasher) when electricity prices are low.  

**Note**: Electrical appliances like washing machines should only be used when awake. Use at your own risk.  

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
  day:
    program: dishcare_dishwasher_program_eco_50
    running_time: 3
  night:
    program: dishcare_dishwasher_program_night_wash
    running_time: 4
```

---

### 🧺 `appliance_notify`  
**Function**: Notifies when a dryer finishes (based on power sensor).  

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

---

### 🚪 `bathroomWindow`  
**Requirements**: [ad-Weather](https://github.com/Pythm/ad-Weather)  
**Function**: Notifies when bathroom humidity drops and window is open.  

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
```

---

### 🌐 `change_dns_cloudflare`  
**Function**: Updates Cloudflare DNS with your public IP.  

**Setup Instructions**:  
- **cloudflare_api_token**: Generate one at your profile → **Authentications**. Use the **Edit Zone DNS** template.  
- **zone_id**: Found at the **Overview page** on [dash.cloudflare.com](https://dash.cloudflare.com).  
- **dns_record_id**: Use the **List DNS Records** API call to find it:  
  [https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records](https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records)  

```yaml
update_cloudflare_dns:
  module: change_dns_cloudflare
  class: Change_DNS
  cloudflare_api_token: !secret cloudflare_api_token
  zone_id: yourCloudflareZoneID
  dns_record_id: yourCloudflareZoneID
  enable_proxy: False
```

---

### 🔐 `door_guard`  
**Function**: Notifies if a door/window is left open for a specified duration.  

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
```

---

### 🎵 `doorbell`  
**Function**: Captures snapshots, sends notifications, and controls media players.  

```yaml
doorbell:
  module: doorbell
  class: Doorbell
  notify_reciever:
    - Me
    - Mykid
  doorbell: binary_sensor.front_door_ding
  camera: camera.front_door_live_view
  media_player:
    - media_player.appletv
```

---

### 🚪 `end_vacation`  
**Function**: Automatically ends vacation mode on presence or datetime.  

```yaml
vacation_end:
  module: end_vacation
  class: endVacation
  vacation_switch:
    - input_boolean.vacation
    - input_boolean.vacation_ac
  presence:
    - person.me
```

---

### ☕ `espresso_machine`  
**Function**: Notifies if the coffee machine is still on at 15:00.  

**iOS Toggle**:  
- Add an iOS toggle (e.g., `ios_toggle: espresso`) to manually turn the machine on/off.  

```yaml
rancilio:
  module: espresso_machine
  class: EspressoMachine
  espresso_machine: switch.kitch_espresso
  notify_reciever:
    - Me
  notify_title: 'Coffee'
  notify_message: 'Coffee machine is still on'
```

---

### 🔥 `fire_alarm`  
**Requirements**: [ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement)  
**Function**: Integrates with fire alarms, mode management, and device control.  

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
**Function**: Opens/closes garage doors via iOS, auto-opens on presence, and sends notifications.  

```yaml
garagecover:
  module: garagedoor
  class: GarageDoor
  garage: cover.garage_door
  auto_open:
    - input: input_boolean.auto_open_garage
      presence: person.me
  notify_reciever:
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
  - `input_text: input_text.cost_pr_month` (for apartment)  
  - `guestUse: input_boolean.easeelader_guest_charging` (for guest)  

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

### 🚫 `media_stop`  
**Function**: Stops media players when a sensor (e.g., doorbell) is triggered.  

```yaml
stop_AppleTv:
  module: media_stop
  class: MediaStop
  sensors:
    - binary_sensor.front_door_ding
  mediaplayer:
    - media_player.loft
```

---

### 📱 `notify_mobiles`  
**Function**: Central notification hub for all apps.  

**Special Features**:  
- **Siri Messages**: Use custom messages for iOS events (e.g., `siri_message: message: food`). To send notifications and update `MODE_CHANGE` used in Lightwand.
- **Notify on State Change**: Sends notifications when a specific sensor changes state (e.g., `sensor.myip`).  

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
    - message: night # Just for calling night mode from iOS event
      
  notify_state_change:
    - sensor: sensor.myip
      notify_title: 'New IP adresse'
      notify_message: 'New IP adresse is'
      notify_reciever:
        - Email
        - Me
```

---

### 🌧️ `rain_notify`  
**Function**: Notifies when rain or wind conditions are met.  

```yaml
notify_on_rain:
  module: rain_notify
  class: Rain_Notify
  rain_sensor:
    - sensor.netatmo_regnsensor_rain
  rain_amount: 0.1
  notify_reciever:
    - Me
```

---

### 🚪 `simultaneousOpened`  
**Function**: Notifies if multiple sensors (e.g., door and window) are open simultaneously.  

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

---

### 🕒 `wake_up`  
**Function**: Custom wake-up alarm with lights, media, and conditions.  

```yaml
wake_up_alarm:
  module: wake_up
  class: WakeUp
  country_code: 'NO'
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

---

## 📝 Additional Notes  

### Support  
For issues or questions, contact [Pythm via GitHub](https://github.com/Pythm).  

---

## 📌 License  
All apps are distributed under the **MIT License**. Use at your own risk.  


