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

## 🧊 **Appliance Home Connect – Start appliances in Home Connect integration**

**🧩 Purpose** – `appliance_home_connect` starts appliances via the Home Connect integration during the cheapest electricity periods. It supports separate day and night programs, remote start via a switch and vacation mode detection.


**✨ Key Features**

| Feature | How it works |
|---------|-------------|
| **Smart scheduling** | Automatically picks cheapest time slots for washing |
| **Day/Night programs** | Different programs for daytime (7 AM-4 PM) and nighttime |
| **Manual override** | Notification buttons let you force-start a program |
| **Away mode** | Pauses scheduling when you're on vacation |

**Safety Note**: Electrical appliances like washing machines should only be used when awake. Use at your own risk.

**🔧 Example Configuration**

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

  options:
    - run_during_nightmode                          # Calculate times when night mode is activated
    - run_during_awaymode                           # Calculate times when away mode is activated during daytime

  # 4️⃣ Program definitions
  day:                                              # Daytime program (runs 07:00-16:00)
    program: dishcare_dishwasher_program_eco_50     # Program name in Home Connect
    running_time: 3                                 # Hours (default: 3)
    finish_by: 16                                   # Hour to finish at latest
  night:                                            # Nighttime program (runs 16:00-07:00)
    program: dishcare_dishwasher_program_night_wash # Program name in Home Connect
    running_time: 4                                 # Hours (default: 4)
    finish_by: 7                                    # Hour to finish at latest
```

**📝 Notes**
- The app works if your washing machine is controlled via Home Connect integration or can be started via the select entity.
- `running_time` must match the actual program duration.


---

## ⚡ Appliance Notify – Notification for Appliances

**🧩 Purpose** – `appliance_notify` watches appliances for a drop in power usage (finished program) and notifies the chosen users.  
It can automatically turn off the appliance and turn it back on after a minute.

**🔧 Example Configuration**

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

**📝 Notes**
- Listens for the power sensor to go above 100 W, waits 30 s for it to drop below 15 W, then notifies.
- If `dryer_switch` is provided, the notification contains a **Turn Off** button; clicking it turns the appliance off.
-  If it finishes during the time window defined by turn_off_after and turn_off_before, the app automatically turns off the switch (if defined) to prevent beeping noises (e.g., from a tumble dryer).
- If turned off by notification or time the switch is turned back on automatically after 60 seconds leaving the machine ready to be used again without any manual interference.


---

## 🛁 Bathroom Window - Reminder to close the windows

**🧩 Purpose** – `bathroomWindow` monitors door/window sensors that stay open for a set duration while humidity drops to normal.  
When the door/window has been open long enough *and* the humidity is back to a comfortable level, a notification is sent to the chosen recipients. The notification can be silenced via a “Do not remind me” action.

**📌 Requirements**: [ad-Weather](https://github.com/Pythm/ad-Weather) 

**🔧 Example Configuration**

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

## 🌐 Change DNS Cloudflare – Updates a Cloudflare `A`‑record with the current public IP.

**🧩 Purpose** – Updates your DNS records with your new IP

**✨ Key Features**

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

**⚙️ Configuration Options**

| Argument | Type | Description | Required |
|----------|------|-------------|----------|
| `cloudflare_api_token` | string | Cloudflare API token (Bearer). | **Yes** |
| `zone_id` | string | ID of the zone that contains the record. | **Yes** |
| `dns_record_id` | string | ID of the Cloudflare DNS record to update. | **Yes** |
| `enable_proxy` | bool | Whether Cloudflare’s *proxy* should be enabled (`proxied: true`). Defaults to `true`. | No |
| `ip_sensor` | string | Home Assistant sensor that holds the public IP.  If omitted the app polls `https://api.ipify.org` every hour. | No |


**🔧 Example Configuration**

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

## 🔐 Door Guard - Reminder to close door / window

**🧩 Purpose** – The DoorGuard app watches a list of door/window sensors and notifies when a sensor remains **open** for a set amount of time.  
When the sensor finally closes, the notification is cleared automatically.  
The app also lets you dismiss a reminder permanently with the **“Do not remind me”** action.

**⚙️ Configuration Options**

| Key | Description | Required |
|-----|-------------|----------|
| `sensors` | List of sensor objects.  Each object must contain: | ✓ |
| &nbsp;&nbsp;&nbsp;&nbsp;`sensor` | Home Assistant entity ID of the door/window sensor. | |
| &nbsp;&nbsp;&nbsp;&nbsp;`duration` | Seconds the sensor must stay `on` before a notification is sent. | |
| `notify_receiver` | List of recipients (labels from the **Notify Mobiles** recipients section). | ✓ |
| `notify_title` | Notification title that appears on the device. | ✓ |
| `notify_message` | Body of the notification. | ✓ |

**🔧 Example Configuration**

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

---

## 📡 Doorbell - Snapshot notifications

**🧩 Purpose** – `doorbell.py` turns a Home Assistant **binary_sensor** into a notfication with camera snapshot:

**✨ Key Features**

| Feature | What it does |
|---------|--------------|
| **Snapshot** | On activation, capture a JPEG from `camera.camera_live_view` → `www/snapshots/`. |
| **Stream** | Optional `media_player` list receives a `camera.play_stream` command (pauses any current playback). |
| **Chime** | Daily volume switch: `daytime_volume` (06:00‑22:00) → `nighttime_volume`. |
| **Notify** | Phone push via `notify_mobiles`.  Uses `notify_receiver`, `notify_message`, and `notify_when_away`. |

**🔧 Example Configuration**

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

## ☀️ End Vacation - Turns off the vacation switch before you return home

**🧩 Purpose** – A helper app that automatically turns off vacation input‑booleans (`input_boolean`) when a given datetime is reached. This will get temperatures back to normal when using my Climate and Electricity Management apps, in addition to run the vacuum and dishwasher and other functions built into in my other apps.

**⚙️ Configuration Options**

| Key | Type | Required? | Description |
|-----|------|-----------|-------------|
| `vacation_switch` | list of `input_boolean` entity IDs | **Yes** | Boolean switches that control vacation mode. |
| `presence` | list of `person` entity IDs | No | Person trackers that trigger the vacation‑end logic when they return home. |
| `vacation_ends` | `input_datetime` entity ID | No | Date/time entity used to schedule the vacation‑end if no presence is detected. |

**🔧 Example Configuration**

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

## ☕ Coffee Machine - Get your Espresso Machine warm and ready to brew in the morning

**🧩 Purpose** – The **Espresso Machine** app monitors your coffee machine and automatically turns the switch on at a time you specify with an `input_datetime` (`coffee_timer`).  
It will notify you if the machine is left on after a user‑defined “last chance” (default 15:00).  

**⚙️ Configuration Options**

| Key              | Type                     | Required? | Description |
|------------------|-----------|-----------|-------------|
| `espresso_machine` | `switch` entity id      | **Yes**   | The switch that controls the coffee machine. |
| `coffee_timer`   | `input_datetime` entity id | **Yes**   | The time at which the switch will be turned on each day.  
                                   Set to `00:00:00` to disable the automatic start. |
| `notify_receiver`| list of recipients       | **Yes**   | Who receives the notification. |
| `notify_title`   | string                   | Optional  | Title of the notification. Defaults to **Coffee**. |
| `notify_message` | string                   | Optional  | Body of the notification. Defaults to **Coffee machine is still on**. |
| `last_chance`    | string time (`HH:MM:SS`) | Optional  | Time that the app will send a “Coffee machine is still on” notification each day.  


**🔧 Example Configuration**

```yaml
rancilio:
  module: espresso_machine
  class: EspressoMachine
  espresso_machine: switch.kitch_espresso   # Switch that powers the espresso machine
  coffee_timer: input_datetime.espresso     # Time to auto‑turn on (00:00:00 disables)
  vacation: input_boolean.vacation          # Optional: Disables auto-turn on when on vacation
  notify_receiver:
    - Me
  notify_title: 'Coffee'
  notify_message: 'Coffee machine is still on'
  last_chance: '16:30:00'                   # Optional – overrides the default 15:00 notification
```

- **Automatic turn‑on**  
  The app calls the Home Assistant service `switch/turn_on` each day at the time defined by `input_datetime.espresso`.  

- **Daily “last chance” notification**  
  At the time specified by `last_chance`, the app checks whether the coffee machine is still on.  
  If it is, it sends a notification that includes a “Turn Off” action button.  
  Clicking that button will immediately turn the machine off.  
  The notification will be sent **even if you are not home** as a safety precaution


**📱 Using the “Turn Off” Button**

When the notification is shown at `last_chance`, you’ll see an action button labeled **Turn Off**.  
When you tap it, the app receives the event `mobile_app_notification_action` and turns the switch off immediately.


---

## 🔥 Fire Alarm - Safety app to handle automations in case of fire

**🧩 Purpose** - App that reacts to fire‑alarm triggers. Communicates via `MODE_CHANGE` to other apps like [ad-ElectricalManagement](https://github.com/Pythm/ad-ElectricalManagement), [ad-ClimateCommander](https://github.com/Pythm/ad-ClimateCommander) and [ad-Lightwand](https://github.com/Pythm/ad-Lightwand) that have built in procedures to stop charging car, turn down heaters and turn on maximum light in addition to the built in functions like turning off all media-players, open all screens and garage doors and turn off any 

**✨ Key Features**

| Function | What it does |
|----------|--------------|
| **Mode change** | Fires a `MODE_CHANGE` event with the `fire` mode when the alarm turns **on**, and a `false_alarm` mode when it returns to **off**. |
| **Safety actions** | Turns off any configured switches, media players, or other devices; opens any configured covers/screens if any person is home. |
| **Notification** | Sends a “Smoke detected” notification through the configured *Notify Mobiles* app, even if no‑one is home. |

**📌 Requirements**
- Depends on the **[ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement)** app for checking whether anyone is home.  

**🔧 Example Configuration**

```yaml
firealarm:
  module: fire_alarm
  class: FireAlarm

  modeManagementApp: manageModes        # AppDaemon name of the ModeManagement app
  dependencies:
    - manageModes
  notify_receiver:                      # List of people (or services) to receive the notification
    - Me

  alarms:                               # List of fire‑alarm binary sensors to monitor
    - binary_sensor.zone_1_smoke

  turn_off:                             # Optional devices/services to turn off when fire alarm is on
    - switch.dishwasher_power
    - fan.mi_air_purifier

  screens:                              # Optional cover/screen entities to open if any person is home
    - cover.screen
    - cover.garage_door
```

* **Alarm turns on**  
  1. Triggers a `MODE_CHANGE` event (`mode: Fire`).  
  2. Turns off all devices listed in `turn_off` that are currently `on`.  
  3. If any person is home, opens every cover in `screens` that is not already open, like garage door etc.
  4. Sends the “Smoke detected” notification to `notify_receiver` (always, even if no‑one is home).

* **Alarm turns off**  
  Fires a `MODE_CHANGE` event with `mode: false-alarm`.

**📱 Additional Notes**
- The app automatically adds all `media_player.*` entities not already in `turn_off` to the turn‑off list.  


---

## 🚗 Garage Door – Auto‑Open & Check of Garage doors

**🧩 Purpose** - A app that automatically opens a garage cover when a chosen presence tracker returns home, and sends a photo‑notification with a “Close” button if the cover remains open during *night* or *away* mode.

**📌 Requirements**
A [ad-Lightwand](https://github.com/Pythm/ad-Lightwand) app that supplies `translations_lightmodes` for mode events.

**⚙️ Configuration Options**

| Argument | Type | Required? | Description |
|----------|------|-----------|-------------|
| `garage` | `cover` entity id | **Yes** | The cover entity that represents the garage door, e.g., `cover.garage_door`. |
| `notify_receiver` | `list` | **Yes** | List of people (or services) that should receive the notification. |
| `target_directory` *(optional)* | `string` | Optional | Directory in the Home‑Assistant web‑root where snapshots will be stored. Defaults to `www/snapshots/`. |
| `camera` *(optional)* | `camera` entity id | Optional | Camera used to take a picture that will be included in the notification. |
| `auto_open` | `list[dict]` | **Yes** | List of dictionaries that define auto‑opening rules:<br>• `presence`: Presence tracker that, when `home`, triggers the garage cover to open.<br>• `switch` (optional): `input_boolean` that will be turned `off` after the cover opens. |

**🔧 Example Configuration**

```yaml
garagecover:
  module: garagedoor
  class: GarageDoor
  target_directory: '/var/lib/docker/volumes/hass_config/_data/www/doorbell/'
  garage: cover.garage_door
  auto_open:
    - switch: input_boolean.auto_open_garage
      presence: person.me
  notify_receiver:
    - Me
  camera: camera.camera_garage
```

1. **Auto‑Open** – When the `switch` turns `on`, the app waits for the specified `presence` to become `home`. It then opens the garage and turns the switch `off`.  
2. **Mode Check** – On a `MODE_CHANGE` to `away` or `night`, if the cover isn’t closed the app sends a notification with a “Close” action (and a snapshot if a camera is set).  
3. **Close Action** – Tapping the “Close” button triggers a `mobile_app_notification_action` that closes the cover.


---

## 📊 Log Energy Usage - Keep history of your usage

**🧩 Purpose** – A electricity logger that writes monthly energy consumption to CSV files and calculates cost‑by‑item, with optional per‑kWh pricing and guest‑usage tracking.  

**📌 Requirements**
- Depends on the **[ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc)** for calculations of price.

**✨ Key Features**

| Feature | What it does |
|---------|--------------|
| **Monthly total** | Give one item the name "Total" to calculate the average price and total cost for the month. |
| **Item‑specific logging** | Log any sensor you wish. |
| **Guest‑usage tracking** | If an `input_boolean` is set to *True*, the app records guest charging consumption and can notify you of the cost. |
| **Print to UI** | Define an `input_text` to print the cost each month to the UI. |
| **CSV output** | Stores each item’s daily data in a CSV file inside a folder of your choice. |

**🔧 Example Configuration**

```yaml
log_energy_usage:
  module: log_energy_usage
  class: LogEnergyUsage
  dependencies:
    - electricalPriceCalc      # Required for price calculation
  csv_folder_path: '/conf/db/'  # Folder where CSV files are written
  items:
    - name: Total
      entity: sensor.last_meter_consumption_home          # Main meter sensor
    - name: Apartment
      entity: sensor.appartment_electric_consumption_kwh  # Apartment‑specific sensor
      input_text: input_text.cost_pr_month                # Cost per kWh (optional)
      namespace_input_text: hass_appartment              # Custom namespace for the input_text
    - name: Easee
      entity: sensor.leia_levetidsforbruk                  # Easee‑specific sensor
      guestUse: input_boolean.easeelader_guest_charging   # Guest‑usage toggle (optional)
      namespace_guest: hass_main                          # Custom namespace for the guestUse
```


---

## 🎵 Pause Media - on absence

**🧩 Purpose** – Pauses any configured media players when **all** sensors in the `sensors` list become `off` for at least 60 seconds.  
When any sensor turns back to `on`, the paused media players are automatically resumed.

**✨ Key Features**

- Works with multiple media players (`media_player` list).  
- Uses the Home Assistant services `media_player/media_pause` and `media_player/media_play`.

**🔧 Example Configuration**

```yaml
pause_kids_room:
  module: media_pause
  class: MediaPause
  sensors:
    - binary_sensor.presence_sensor_rom   # sensor that triggers pause/resume
  media_player:
    - media_player.roon                   # media player(s) to control
  # Use Appdaemons built in constraints to define when app runs
  constrain_start_time: "07:30:00"
  constrain_end_time:   "20:00:00"
```


---

## ⏹️ Stop Media players - on sensor triggered

**🧩 Purpose** – Stops any media player that is currently playing when a specified sensor turns **on**.

**✨ Key Features**

| Feature | What it does | How to use |
|---------|--------------|------------|
| **Sensor‑triggered stop** | Monitors each sensor in `sensors`. When the sensor changes to `on`, the app calls `media_player/media_stop` on all configured media players. | Add one or more sensors under `sensors`. |
| **Conditional listening** | If an `activate_switch` is configured, the app will only start listening to the sensors when that switch is turned **on** (and will stop listening when it goes **off**). | Provide an `activate_switch` entity ID. |

**🔧 Example Configuration**

```yaml
stop_AppleTv:
  module: media_stop
  class: MediaStop
  sensors:                # Sensors that trigger a stop
    - binary_sensor.front_door_ding
  media_player:           # Media players that will be stopped
    - media_player.appleTV
  # Optional: start listening only when this switch turns on
  activate_switch: input_boolean.enable_media_stop
```


---

## 📱 **Notify Mobiles – Central Notification Hub**

**🧩 Purpose** – `notify_mobiles` is the single place where all of Pythm’s AppDaemon apps push messages to devices.
You configure the users devices here, and the person name as recipients in the other apps. -> One place to change devices when someone get's a new phone.
It handles three core tasks:

**✨ Key Features**

| Feature | What it does | How you use it |
|---------|--------------|----------------|
| **Central hub** | Forwards a message to any number of mobile/notification services (e.g. `mobile_app_*`, `gmail`, `telegram`, …). | Add a recipient block to `recipients`. |
| **Siri messages** | Lets you trigger a Home Assistant *fire event* from an iOS Shortcut and have the app send a pre‑configured notification to selected users. | Create an iOS Shortcut → *Fire Event* → `event name = ios.lightwand-mode-change` → *Event data* contains `{"message":"food"}`. |
| **State‑change alerts** | Sends a notification automatically whenever a sensor you care about changes value. | Add a `notify_state_change` entry with the sensor entity ID and a short message. |


**🔧 Example Configuration**

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

**🔧 Setting Up Siri Shortcuts (iOS)**

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

## 🌧️ Rain and wind notifications - when windows are open

**🧩 Purpose** – Notifies when it starts to rain or when wind speed is high **and** any of the specified window sensors are open.

**📌 Requirements**
[ad-Weather](https://github.com/Pythm/ad-Weather) 

**✨ Key Features**

The app listens for the `WEATHER_CHANGE` event from the ad-Weather app where you configure all your weather sensors.
The notification lists the friendly names of all open windows

> 📍 *Only sends one notification per 3 hours, regardless of further weather changes.*  

**🔧 Example Configuration**

```yaml
rain_notify:
  module: rain_notify
  class: Rain_Notify

  notify_receiver:                  # (required) Who should receive the message
    - Me

  rain_amount: 0.1                  # (optional) Minimum rain (mm) to trigger notification
  anemometer_speed: 40              # (optional) Minimum wind speed (km/h) to trigger notification

  windowsensors:                    # (required) List of window sensor entities
    - binary_sensor.window_kitchen
    - binary_sensor.window_bedroom
```

> ⚠️ **Tip** – Make sure the window sensors report `on` when open and have a `friendly_name` attribute.  


---

## 🚪 **Simultaneous Door / Window Guard - Reminder**  

**🧩 Purpose** – The `SimultaneousOpened` app watches two sensors (e.g. a door and a window) and alerts you when **both** are opened **simultaneously** for a configurable period.  
It also checks the ambient temperature and only triggers the notification when the temperature is below a given threshold.


**✨ Key Features**

| Feature | What it does | Configuration |
|---------|--------------|---------------|
| **Concurrent‑sensor detection** | Triggers a notification if the primary sensor (`sensors`) and the *simultaneous* sensor (`simultaneous_sensor`) are both `on` for at least the configured duration. | `simultaneous_sensor: binary_sensor.window_door_is_open` |
| **Timed wait** | Each primary sensor must stay `on` for at least `duration` (minimum 71 s) before the check is performed. | `duration: 300` |
| **Temperature filter** | Optional: Only send the alert when the ambient temperature (defined by `temperature_sensor`) is below `check_below_temp` (default 23 °C). | `check_below_temp: 23` |
| **Clear notification** | When any of the monitored sensors turns `off`, the notification is automatically cleared. | — |

---

**🔧 Example Configuration**

```yaml
simultaneousOpened:
  module: simultaneousOpened
  class: SimultaneousOpen

  notify_receiver:                # Who should receive the message
    - MyKid

  sensors:                        # List of primary sensors to watch
    - sensor: binary_sensor.door_contact
      duration: 300                # Seconds the sensor must stay 'on' before the check runs

  simultaneous_sensor: binary_sensor.window_door_is_open # Secondary sensor to watch
  temperature_sensor: sensor.temperature                 # Optional temperature sensor
  check_below_temp: 23                                   # Optional: temp threshold

  notify_title: 'Both door and window is open'
  notify_message: 'Close either'
```


---

## 🌞 Wake Up – Custom Wake‑up Alarm

**🧩 Purpose** – **Central hub for a fully‑automatic morning routine** – play a playlist, adjust volume, light up the room, and honor holidays and vacations.

**📌 Requirements**
- Python packages **geopy** and **holliday** listed in requirements.txt. If running Appdaemon addon please add the packages like this: https://github.com/Pythm/ad-ModeManagement/issues/15#issuecomment-3688156477

**✨ Key Features**

| Feature | What it does | How to use |
|---------|--------------|------------|
| **Alarm switches** | `alarm_switch` (workdays) and `alarm_switch_non_work_day` (holidays) decide whether music should start. | Provide an `input_boolean` to turn on and off. |
| **Holiday detection** | Uses the `holidays` library; if a country code is supplied, the holidays for that country are used. If no country code, the location is derived from the Home Assistant latitude/longitude via `geopy`. | `country_code: 'NO'` – or let the app geolocate. |
| **Vacation state** | `vacation` (`input_boolean.vacation` by default) stops all actions while on. | Provide the entity or let the app default to `input_boolean.vacation`. |
| **Music** | Plays the specified `playlist` on the defined `media_player` with optional volume. | `media_player: media_player.bedroom`, `playlist: Playlists/Morning`, `volume: 0.2`. |
| **Lights** | Turns on the list of `wake_up_lights` (Home Assistant) and/or publishes to MQTT topics `wake_up_MQTTlights` with `light_data` payload. | `wake_up_lights: [light.bedroom_light]`, `wake_up_MQTTlights: [zigbee2mqtt/HueGradient]`, `light_data: {"brightness": 80, "effect": "sunrise"}` |
| **Scheduling** | The wake‑up time is read from an `input_datetime` entity.  The app sets a daily timer for music and a (possibly offset) timer for lights.  Changing the time updates the timers automatically. | `time: input_datetime.wakeup` |
| **Conditions** | Optional Python expressions (strings) that must all evaluate to `True` before any action is taken (e.g. `self.get_state('person.wife') == 'home'`). | `conditions: ["self.get_state('person.wife') == 'home'"]` |
| **Time‑offset** | `light_time_offset` adds minutes to the light‑turn‑on time so lights can start slightly earlier or later than music. | `light_time_offset: 5` |


**📦 Required Entities**

- `media_player` – one or more media players (must accept `play_media`).  
- `playlist` – a valid media item ID that can be played by the media player.  
- `wake_up_lights` – Home Assistant light entities.  
- `wake_up_MQTTlights` – MQTT light topics that accept JSON payloads.  
- `time` – an `input_datetime` entity that holds the daily wake‑up time.

**🔧 Example Configuration**

```yaml
wake_up_alarm:
  module: wake_up
  class: WakeUp
  country_code: 'NO'
  vacation: input_boolean.vacation
  alarm_switch: input_boolean.alarm_switch_workday   # optional; default if entity missing
  alarm_switch_non_work_day: input_boolean.alarm_switch_holidays  # optional
  media_player: media_player.bedroom
  playlist: Playlists/Morning
  volume: 0.2
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
