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
All apps uses the `notify_mobiles` app by default (named `notify_mobiles`). If you rename this app, configure other apps with the `notify_app` parameter and the new name. You can also configure my public apps with `notify_app: notify_mobiles` to get additional notification functionality.

My public apps with notification:
- [ad-ClimateCommander](https://github.com/Pythm/ad-ClimateCommander)
- [ad-ElectricalManagement](https://github.com/Pythm/ad-ElectricalManagement)
- [ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement)

```yaml
  notify_app: notify_mobiles          # Name of your notification app
```

> [!TIP]  
> Long press notification for options

### 🔧 Namespace Configuration  
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
**Most sensors that are not critical to the app’s functionality are optional.**

#### Index of apps

🔔 **[Notify Mobiles – Central Notification Hub](https://github.com/Pythm/Pythm_AppdaemonApps#-notify-mobiles--central-notification-hub)**

A single app that routes all alerts to mobile devices, supports Siri‑shortcuts, and can be triggered by state changes.  
Key features:  
- **Recipients**: list of people with their Home Assistant trackers and notification receivers.  
- **Siri messages**: custom Home Assistant events fired from iOS that send a pre‑configured message to chosen recipients.  
- **State‑change alerts**: automatically notify when any sensor in `notify_state_change` toggles.  
- **Mode change**: iOS‑shortcuts fire `ios.lightwand-mode-change`, which is logged as a `MODE_CHANGE` event for other apps. |


🧊 **[Appliance Home Connect](https://github.com/Pythm/Pythm_AppdaemonApps#-appliance-home-connect--start-appliances-in-home-connect-integration)**

Auto-schedules appliances during *cheapest power hours* saving you money on electricity. Separate day and night programs.


| App | Short Description |
|-----|-------------------|
| `appliance_notify` | Notifies you when an appliance finishes, optionally silencing the unit automatically. |
| `bathroomWindow` | Alerts when humidity drops while a bathroom window is open – a simple leak‑prevention tool. |
| `change_dns_cloudflare` | Keeps your Cloudflare DNS record in sync with your public IP. |
| `door_guard` | Warns when a door/window is left open beyond a set duration (e.g., fridge door). |
| `doorbell` | Captures a snapshot, sends a notification, and streams to media players when the doorbell rings. |
| `end_vacation` | Automatically turns off vacation mode when people return or a scheduled date arrives. |
| `espresso_machine` | Sends a warning if your coffee machine is left on after a set time. |
| `fire_alarm` | Integrates fire alarms, mode‑management, and device shutdown on danger detection. |
| `garagedoor` | Opens/closes your garage door via iOS and auto‑opens on presence. |
| `log_energy_usage` | Logs energy usage & calculates monthly cost, including guest‑usage adjustments. |
| `media_pause` | Pauses media players when an associated sensor goes inactive (e.g., no one in room). |
| `media_stop` | Stops media players when a sensor (e.g., doorbell) is triggered. |
| `rain_notify` | Notifies when rain or wind conditions meet your thresholds. |
| `simultaneousOpened` | Warns when multiple sensors (door + window) are open at the same time. |
| `wake_up` | Custom wake‑up alarm that can turn on lights, play a playlist, and more. |


---

### 🧊 **Appliance Home Connect – Start appliances in Home Connect integration**

**Purpose** – `appliance_home_connect` starts appliances via the Home Connect integration during the cheapest electricity periods. It supports separate day and night programs, remote start via a switch and vacation mode detection.


#### ✨ Key Features

| Feature | How it works |
|---------|-------------|
| **Smart scheduling** | Automatically picks cheapest time slots for washing |
| **Day/Night programs** | Different programs for daytime (7 AM-4 PM) and nighttime |
| **Manual override** | Notification buttons let you force-start a program |
| **Away mode** | Pauses scheduling when you're on vacation |

**Safety Note**: Electrical appliances like washing machines should only be used when awake. Use at your own risk.

#### 📌 Configuration Overview

Below is a fully-annotated example showing every configuration option the app understands. Copy-paste into your `apps.yaml` and adjust:

```yaml
name-your-app:
  module: appliance_home_connect
  class: HomeConnect
  dependencies:
    - electricalPriceCalc

  # 1️⃣ Notification settings
  notify_receiver:                    # Who gets notified (must match person labels in notify_mobiles)
    - Me
    - MyWife

  # 2️⃣ Vacation/away state
  vacation: input_boolean.vacation    # Optional: pauses scheduling when on vacation

  # 3️⃣ Appliance control
  remote_start: binary_sensor.remote_start_machine  # Switch that enables remote start
  active_program: select.dishwasher_program         # Select entity for program choice

  # 4️⃣ Program definitions
  day:                                              # Daytime program (runs 07:00-16:00)
    program: dishcare_dishwasher_program_eco_50     # Program name in Home Connect
    running_time: 3                                 # Hours (default: 3)
  night:                                            # Nighttime program (runs 16:00-07:00)
    program: dishcare_dishwasher_program_night_wash # Program name in Home Connect
    running_time: 4                                 # Hours (default: 4)
```

#### 📝 Notes
- The app works if your washing machine is controlled via Home Connect integration or can be started via the select entity.
- `running_time` must match the actual program duration.


---

### ⚡ Appliance Notify – Central Notification for Appliances

**Purpose** – `appliance_notify` watches appliances for a drop in power usage (finished program) and notifies the chosen users.  
It can automatically turn off the appliance and turn it back on after a minute.

#### 📌 Configuration Overview

```yaml
tumbledryer:
  module: appliance_notify
  class: Dryer
  dryer_switch: switch.tumble_dryer      # Switch that controls the appliance
  dryer_power: sensor.tumble_dryer_power # Sensor that reports power usage
  notify_receiver:
    - Me
    - Email
  notify_title: 'Tumble Dryer'
  notify_message: 'Your dryer has finished its cycle.'
  turn_off_after: '22:00:00'            # Turn the appliance off only between these times
  turn_off_before: '07:00:00'

```

#### 📝 Notes
- Listens for the power sensor to go above 100 W, waits 30 s for it to drop below 15 W, then notifies.
- If `dryer_switch` is provided, the notification contains a **Turn Off** button; clicking it turns the appliance off.
-  If it finishes during the time window defined by turn_off_after and turn_off_before, the app automatically turns off the switch (if defined) to prevent beeping noises (e.g., from a tumble dryer).
- If turned off by notification or time the switch is turned back on automatically after 60 seconds leaving the machine ready to be used again without any manual interference.


---

### 🛁 Bathroom Window

**Requirements**: [ad-Weather](https://github.com/Pythm/ad-Weather)  

**Purpose** – `bathroomWindow` monitors door/window sensors that stay open for a set duration while humidity drops to normal.  
When the door/window has been open long enough *and* the humidity is back to a comfortable level, a notification is sent to the chosen recipients. The notification can be silenced via a “Do not remind me” action.

#### 📌 Configuration Overview

```yaml
window_and_door:
  module: bathroomWindow
  class: BathroomWindow

  sensors:                     # List of door/window sensors to monitor
    - sensor: binary_sensor.door_contact
      duration: 1200           # Seconds the sensor must stay “on” before checking humidity
    - sensor: binary_sensor.window_contact
      duration: 600

  humidity: sensor.humidity   # Optional humidity sensor
  offset: 5                   # Acceptable humidity difference from average

  check_below_temp: 20        # Only notify when outside temperature is below this value

  notify_receiver:
    - Me
  notify_title: 'Bathroom Window Open'
  notify_message: 'Humidity is down to normal'
```

* `notify_receiver` is mandatory (used by `notify_mobiles`), while `notify_title` and `notify_message` default to “Bathroom Window Open” and “Humidity is down to normal” if omitted.*


---

### 🌐 **Change DNS Cloudflare** – Updates a Cloudflare `A`‑record with the current public IP.

**What the app does**

- If a Home Assistant `ip_sensor` is supplied, it listens for state changes on that sensor and triggers an update when a new IP is reported.  
- If no sensor is provided, it:
   * fetches the public IP once during startup (`_get_public_ip`)  
   * checks the public IP every hour at 00:10 (`_checkPublicIPAddress`).  
- Whenever the public IP differs from the record IP, the app sends a `PUT` request to Cloudflare to update the record.  

**Setup Instructions**:  

- **cloudflare_api_token**: Generate one at your profile → **Authentications**. Use the **Edit Zone DNS** template.  
- **zone_id**: Found at the **Overview page** on [dash.cloudflare.com](https://dash.cloudflare.com).  
- **dns_record_id**: Use the **List DNS Records** API call to find it:  
  [https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records](https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records)  

| Argument | Type | Description | Required |
|----------|------|-------------|----------|
| `cloudflare_api_token` | string | Cloudflare API token (Bearer). | **Yes** |
| `zone_id` | string | ID of the zone that contains the record. | **Yes** |
| `dns_record_id` | string | ID of the Cloudflare DNS record to update. | **Yes** |
| `enable_proxy` | bool | Whether Cloudflare’s *proxy* should be enabled (`proxied: true`). Defaults to `true`. | No |
| `ip_sensor` | string | Home Assistant sensor that holds the public IP.  If omitted the app polls `https://api.ipify.org` every hour. | No |

#### 📌 Configuration Overview

```yaml
update_cloudflare_dns:
  module: change_dns_cloudflare
  class: Change_DNS
  cloudflare_api_token: <your-token>
  zone_id: <your-zone-id>
  dns_record_id: <your-record-id>
  enable_proxy: true          # optional – defaults to true
  # ip_sensor: sensor.my_public_ip  # optional; omit to use ipify polling
```


---

### 🔐 Door Guard

The DoorGuard app watches a list of door/window sensors and notifies when a sensor remains **open** for a set amount of time.  
When the sensor finally closes, the notification is cleared automatically.  
The app also lets you dismiss a reminder permanently with the **“Do not remind me”** action.

```yaml
fridge:
  module: door_guard
  class: DoorGuard

  sensors:
    - sensor: binary_sensor.window_door_is_open
      duration: 300          # seconds to wait before the notification is sent
  notify_receiver:
    - Me
    - MyKids
  notify_title: 'Name Your Door/Window'
  notify_message: 'Your notification'
```

#### Configuration keys

| Key | Description | Required |
|-----|-------------|----------|
| `sensors` | List of sensor objects.  Each object must contain: | ✓ |
| &nbsp;&nbsp;&nbsp;&nbsp;`sensor` | Home Assistant entity ID of the door/window sensor. | |
| &nbsp;&nbsp;&nbsp;&nbsp;`duration` | Seconds the sensor must stay `on` before a notification is sent. | |
| `notify_receiver` | List of recipients (labels from the **Notify Mobiles** recipients section). | ✓ |
| `notify_title` | Notification title that appears on the device. | ✓ |
| `notify_message` | Body of the notification. | ✓ |


---

### 📡 Doorbell

`doorbell.py` turns a Home Assistant **binary_sensor** into a notfication with camera snapshot:

| Feature | What it does |
|---------|--------------|
| **Snapshot** | On activation, capture a JPEG from `camera.camera_live_view` → `www/snapshots/`. |
| **Stream** | Optional `media_player` list receives a `camera.play_stream` command (pauses any current playback). |
| **Chime** | Daily volume switch: `daytime_volume` (06:00‑22:00) → `nighttime_volume`. |
| **Notify** | Phone push via `notify_mobiles`.  Uses `notify_receiver`, `notify_message`, and `notify_when_away`. |

#### 📌 Configuration Overview

```yaml
doorbell_alarm:
  module: doorbell
  class: Doorbell
  target_directory: 'www/snapshots/'
  notify_receiver:
    - Me
    - MyKids
  notify_message: 'Someone at the door'
  notify_when_away: True
  doorbell: binary_sensor.front_door_ring

  # Chime (optional)
  chime: number.daily_chime_volume
  daytime_volume: 80
  daytime_start: '06:00:00'
  nighttime_volume: 30
  daytime_stop: '22:00:00'

  # Camera & stream (optional). Have not gotten this to work on Apple TV's
  camera: camera.front_door_live_view
  media_player:
    - media_player.living_room_tv
```

**Tip:** Target directory is specific to your installation.
> Proxmox Helper Script Home Assistant Container -> '/var/lib/docker/volumes/hass_config/_data/www/snapshots/'


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

#### ✨ Key Features

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

### 📱 **Notify Mobiles – Central Notification Hub**

**Purpose** – `notify_mobiles` is the single place where all of Pythm’s AppDaemon apps push messages to devices.
You configure the users devices here, and the person name as recipients in the other apps. -> One place to change devices when someone get's a new phone.
It handles three core tasks:

| Feature | What it does | How you use it |
|---------|--------------|----------------|
| **Central hub** | Forwards a message to any number of mobile/notification services (e.g. `mobile_app_*`, `gmail`, `telegram`, …). | Add a recipient block to `recipients`. |
| **Siri messages** | Lets you trigger a Home Assistant *fire event* from an iOS Shortcut and have the app send a pre‑configured notification to selected users. | Create an iOS Shortcut → *Fire Event* → `event name = ios.lightwand-mode-change` → *Event data* contains `{"message":"food"}`. |
| **State‑change alerts** | Sends a notification automatically whenever a sensor you care about changes value. | Add a `notify_state_change` entry with the sensor entity ID and a short message. |

---

#### 📌 Configuration Overview

Below is a fully‑annotated example that shows every configuration option the app understands.  
Feel free to copy‑paste it into your own `apps.yaml`, adjust and tweak the comments.

```yaml
notify_mobiles:
  module: notify_mobiles
  class: Notify_Mobiles

  # ── 1️⃣ Recipients ───────────────────────────────────────
  recipients:                  # List of people (or services) that can receive notifications
    - person: Me               # “person” is an arbitrary label – used in the code to identify who gets the message
      receiver:                # One or more notification services that belong to this person
        - mobile_app_my_phone
      tracker: person.me       # Optional: a Person tracker entity – used to decide “when to send”
    - person: MyKids
      receiver:
        - mobile_app_my_first_kid
        - mobile_app_my_second_kid
    - person: Email
      receiver:
        - gmail                # You can add any notification service that Home Assistant supports

  # ── 2️⃣ Siri‑message blocks ───────────────────────────────────────
  siri_message:                # List of custom events that can be fired from iOS Shortcuts
    - message: food            # The value that will be passed in the event payload (`{"message":"food"}`)
      notify_receiver:         # Who should see the notification
        - MyKids
      notify_title: 'Food'     # Title of the notification
      notify_message: 'Food is on the table!'  # Body of the notification

  # ── 3️⃣ State‑change alerts ───────────────────────────────────────
  notify_state_change:         # One or more entries – the app will fire a notification whenever the sensor changes
    - sensor: sensor.myip
      notify_title: 'New IP address'
      notify_message: 'New IP address is '
      notify_receiver:
        - Email
        - Me
```

---

#### 🔧 Setting Up Siri Shortcuts (iOS)

If you want to use Siri to *trigger a mode change* (e.g. “Food” or “Movie”) and automatically send a notification:

1. Open **Shortcuts** on your iPhone.  
2. Create or edit a shortcut.  
3. Add **Action** → *Home Assistant* → **Fire Event**.  
4. **Configure the event**  
   * **Event name** – `ios.lightwand-mode-change` (keep this the same for all shortcuts).  
   * **Event data** – JSON that contains the message you want to send, e.g. `{"message":"food"}`.  

> **Example** – *Food*  
> ```json
> {"message":"food"}
> ```  
> **Example** – *Movie*  
> ```json
> {"message":"movie"}
> ```

When the shortcut fires the event, `notify_mobiles` will catch it, look up the matching `siri_message` block, and push the configured notification to the chosen recipients.

---

#### ✨ Key Features Summarized

| Function | How to enable |
|----------|---------------|
| **Central notification** | Define recipients in `recipients`. |
| **Siri messages** | Add a `siri_message` list; set up iOS Shortcut as shown above. |
| **State‑change alerts** | Add a `notify_state_change` list with sensor, title, message, and recipients. |

---

### 🌧️ `rain_notify`

**Requirements**: [ad-Weather](https://github.com/Pythm/ad-Weather)  
**Function**: Notifies when rain or wind conditions are met if a sensor is on.  

**Example configuration**

```yaml
notify_on_rain:
  module: rain_notify
  class: Rain_Notify

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
