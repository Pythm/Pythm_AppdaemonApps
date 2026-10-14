# Pythm's AppDaemon Apps

Small, single-purpose [AppDaemon](https://appdaemon.readthedocs.io/) apps for Home Assistant: notifications, door and window reminders, appliance helpers, a wake-up routine, a fire-alarm handler and a few utilities. Each app is one Python file in [`apps/`](apps), configured in `apps.yaml`. Nothing needs to be edited in the code.

- Tested with AppDaemon **4.5.x** in Docker, connected to Home Assistant.
- MIT license, see [License](#license).
- Larger apps by the same author live in their own repositories: [ad-Lightwand](https://github.com/Pythm/ad-Lightwand), [ad-ClimateCommander](https://github.com/Pythm/ad-ClimateCommander), [ad-ElectricalManagement](https://github.com/Pythm/ad-ElectricalManagement), [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc), [ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement) and [ad-Weather](https://github.com/Pythm/ad-Weather).

> [!IMPORTANT]
> These apps control real devices: doors, heaters, appliances and reactions to a smoke alarm. They are written for the author's own home and shared as-is. Read the notes of an app before you rely on it, and never treat `fire_alarm` as a certified safety system.

## Apps at a glance

| App | What it does | Needs |
|---|---|---|
| [`notify_mobiles`](#notify_mobiles) | Central notification hub. Also turns iOS Shortcuts into modes and alerts on sensor changes. | Companion app |
| [`door_guard`](#door_guard) | Reminds you when a door or window stays open. | `notify_mobiles` |
| [`bathroomWindow`](#bathroomwindow) | Reminds you to close a window when the humidity is back to normal. | `notify_mobiles`, [ad-Weather](https://github.com/Pythm/ad-Weather) (optional) |
| [`simultaneousOpened`](#simultaneousopened) | Alerts when a window and a door are open at the same time. | `notify_mobiles` |
| [`rain_notify`](#rain_notify) | Alerts on rain, wind or darkness while a window is open. | `notify_mobiles`, [ad-Weather](https://github.com/Pythm/ad-Weather) |
| [`garagedoor`](#garagedoor) | Opens the garage when you arrive, warns when it is left open. | `notify_mobiles` |
| [`doorbell`](#doorbell) | Notification with a camera snapshot when the doorbell rings. | `notify_mobiles` |
| [`end_vacation`](#end_vacation) | Turns vacation mode off when someone is home or at a set date. | |
| [`wake_up`](#wake_up) | Music and lights in the morning. | |
| [`appliance_notify`](#appliance_notify) | Notifies when a program (dryer, washer) is finished. | `notify_mobiles` |
| [`appliance_home_connect`](#appliance_home_connect) | Starts a Home Connect appliance at the cheapest time. | `notify_mobiles`, [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc) |
| [`espresso_machine`](#espresso_machine) | Turns a coffee machine on at a set time and reminds you if it is still on. | `notify_mobiles` |
| [`log_energy_usage`](#log_energy_usage) | Logs energy cost per day and month. | `notify_mobiles`, [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc) |
| [`charger_controller`](#charger_controller) | Keeps a device battery between 75 and 80 %. | |
| [`media_pause`](#media_pause) | Pauses media when the room is empty and resumes it. | |
| [`media_stop`](#media_stop) | Stops media when a sensor triggers. | |
| [`fire_alarm`](#fire_alarm) | Reacts to smoke detectors. | `notify_mobiles`, [ad-Lightwand](https://github.com/Pythm/ad-Lightwand) and [ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement) (optional) |
| [`change_dns_cloudflare`](#change_dns_cloudflare) | Keeps a Cloudflare A record equal to your public IP. | |

Apps cooperate through AppDaemon app names, Home Assistant entities and events, not by importing each other. Everything marked optional works without the other repository.

## Quick start

1. Install AppDaemon and connect it to Home Assistant (see the [AppDaemon docs](https://appdaemon.readthedocs.io/en/latest/INSTALL.html)).
2. Clone this repository into your AppDaemon `apps` directory:

   ```bash
   cd /path/to/appdaemon/conf/apps
   git clone https://github.com/Pythm/Pythm_AppdaemonApps.git
   ```

   Pull again later to update. AppDaemon reloads an app as soon as its `.py` file changes.
3. Install the packages in [`requirements.txt`](requirements.txt) if you use `wake_up` (`holidays`). With the AppDaemon add-on, list them under the add-on's `python_packages` option.
4. Add the apps you want to `apps.yaml`. Each app section below has an example. Add `notify_mobiles` first, most other apps need it.
5. Optional: set `missing_app_warnings: 0` in `appdaemon.yaml` to silence warnings about the apps you do not configure.

A first setup, a notification hub and a door reminder:

```yaml
notify_mobiles:
  module: notify_mobiles
  class: Notify_Mobiles
  recipients:
    - person: Me
      receiver:
        - mobile_app_my_phone     # notify.mobile_app_my_phone without "notify."
      tracker: person.me

front_door_guard:
  module: door_guard
  class: DoorGuard
  dependencies:
    - notify_mobiles
  sensors:
    - sensor: binary_sensor.front_door
      duration: 300
  notify_receiver:
    - Me
  notify_title: 'Front door'
  notify_message: 'The front door has been open for 5 minutes'
```

### Set up with an AI assistant

Do not want to look up entity ids and write YAML yourself? [`LLM_GUIDE.md`](LLM_GUIDE.md) tells an AI assistant how to do it for you. A read-only script, [`tools/ha_snapshot.py`](tools/ha_snapshot.py), lists your Home Assistant entities in a local file (git ignores it), and the assistant uses that list to fill in `apps.yaml`. The guide explains how to create the access token and where to put it. The token is never typed into a chat.

## Requirements

| Requirement | Needed by |
|---|---|
| AppDaemon 4.5.x with the HASS plugin | all apps |
| Home Assistant Companion app on phones | actionable notifications (buttons) in most apps. Some options are iOS-only, see each app. |
| `holidays` (pip) | `wake_up`, only with `country_code` |
| `pydantic` (pip) | `simultaneousOpened` (through `ad_config.py`). Normally already installed with AppDaemon 4.x, run `pip install pydantic` if you see an import error. |
| MQTT plugin in AppDaemon | `wake_up`, only with `wake_up_MQTTlights` |

`utils_apps.py` (snapshot helper), `ad_config.py` (config model for `simultaneousOpened`) and `mode_names.py` (mode names, see [Mode names](#mode-names)) are modules, not apps. Do not add them to `apps.yaml`.

---

## Common configuration

Every app section in `apps.yaml` has `module` and `class`, plus the keys it needs. The tables below list only the keys of that app. These keys work the same in every app that has them:

| Key | Apps | Default | Description |
|---|---|---|---|
| `HASS_namespace` | all | `default` | Home Assistant namespace. Only needed with more than one Home Assistant. |
| `notify_app` | all apps that notify | `notify_mobiles` | Name of the notify app, if you called it something else. |
| `notify_receiver` | all apps that notify | | Person labels from `recipients` in `notify_mobiles`, see [Notifications](#notifications). |
| `also_if_not_home` | `door_guard`, `simultaneousOpened`, `rain_notify` | `false` | `true` also notifies people who are away. |
| `vacation` | `appliance_home_connect`, `espresso_machine`, `wake_up` | `input_boolean.vacation` | Vacation helper, see [Vacation helper](#vacation-helper). |
| `dependencies` | all | | AppDaemon: apps that must be loaded first. |
| `log`, `log_level` | all | | AppDaemon: log file and level. `log_level: DEBUG` gives more output. |

### Notifications

`notify_receiver` is a list of the person labels you defined in `recipients` of `notify_mobiles`, not phone service names. A label that does not exist in `notify_mobiles` receives nothing. An empty list notifies nobody. Where `notify_receiver` is optional (`simultaneousOpened`), leaving it out notifies everyone.

Always add the notify app under `dependencies`, so it is loaded before the app that uses it:

```yaml
dependencies:
  - notify_mobiles
```

An app that cannot find its notify app logs an ERROR naming the app.

> [!WARNING]
> AppDaemon starts **no app at all** if a name in `dependencies` does not exist in your configuration. Remove the line when you remove the app.

Who receives a message: a recipient with a `tracker` only receives while the tracker is `home`, unless the app asks to notify people who are away. A recipient without `tracker` always receives. Long press a notification on the phone to see its buttons.

### Vacation helper

The apps with a vacation option fall back to `input_boolean.vacation` when `vacation:` is not set. Set it explicitly to avoid depending on that default. `end_vacation` can turn the helper off automatically.

### Lists

Where a table says "entity, or a list", a single entity and a list both work. Where it says "list", use list syntax.

### Secrets

Put tokens and passwords in AppDaemon's `secrets.yaml` and refer to them with `!secret name`.

### AppDaemon constraints

`constrain_start_time`, `constrain_end_time` and `constrain_days` apply to the whole app. In an app with a safety reminder, such as `espresso_machine`, they also suppress the reminder.

### Mode names

`appliance_home_connect`, `fire_alarm` and `garagedoor` use the same mode names and the `MODE_CHANGE` event as [ad-Lightwand](https://github.com/Pythm/ad-Lightwand). They get them from `mode_names.py`, which uses Lightwand's names when Lightwand is installed and otherwise the English defaults (`MODE_CHANGE`, `automagical`, `night`, `away`, `fire`, `false-alarm`, and so on). Nothing needs to be configured for English.

If you translate modes with Lightwand 2.3.0 or later, start the `ModeTranslation` app first so these apps get your names when they start:

```yaml
mode_translation:
  module: mode_translation
  class: ModeTranslation
  language_file: /conf/persistent/lightwand/translations.json
  language: "no"

fire_alarm:
  module: fire_alarm
  class: FireAlarm
  dependencies: mode_translation
```

---

## Apps

### notify_mobiles

Central notification hub. You define people and their notification services once. Every other app sends to a person label, so a new phone only has to be changed here. It also turns iOS Shortcut events into notifications and can alert on sensor state changes.

```yaml
notify_mobiles:
  module: notify_mobiles
  class: Notify_Mobiles

  recipients:
    - person: Me                     # Label used as notify_receiver in other apps
      receiver:                      # notify services, without the "notify." prefix
        - mobile_app_my_phone
      tracker: person.me             # Optional, see Notifications in Common configuration
    - person: Kids
      receiver:
        - mobile_app_first_kid
        - mobile_app_second_kid

  siri_message:                      # Optional, iOS Shortcuts
    - message: food
      notify_receiver:
        - Kids
      notify_title: 'Food'
      notify_message: 'Food is on the table!'

  notify_state_change:               # Optional, alert when a sensor changes
    - sensor: sensor.my_public_ip
      notify_receiver:
        - Me
      notify_title: 'New IP address'
      notify_message: 'New IP address is'
```

| Key | Required | Default | Description |
|---|---|---|---|
| `recipients` | **Yes** (in practice) | `[]` | List of people. Without it every notification is dropped. |
| `recipients[].person` | **Yes** | | Label other apps use in `notify_receiver`. |
| `recipients[].receiver` | **Yes** | | List of notify service names (`mobile_app_...`). With `send_via: email`, the SMTP notify entities (`notify.my_email`). |
| `recipients[].tracker` | No | none | `person` or `device_tracker` entity. See below. |
| `recipients[].send_via` | No | `notify` | `email` sends with the Home Assistant `smtp.send_message` action, see Email below. |
| `siri_message` | No | none | Each item: `message` (event payload to match). With `notify_receiver`, `notify_title` and `notify_message` all three are needed. |
| `notify_state_change` | No | none | Each item: `sensor`, plus `notify_receiver`, `notify_title`, `notify_message` and optional `namespace`. The message is followed by the new state, also `unavailable` and `unknown`. |
| `ios_event` | No | `ios.lightwand-mode-change` | Name of the iOS event used with `siri_message`. |

The `MODE_CHANGE` event name and the mode names come from [Mode names](#mode-names). The old `lightwand_language` and `language_file` options are ignored.

**Who receives a message.** See [Notifications](#notifications). In short: a recipient with a `tracker` only receives while it is `home`, unless the calling app asks for people who are away.

**Calling it from your own app:**

```python
notify = self.ADapi.get_app('notify_mobiles')
notify.send_notification(
    message='Window open',
    message_title='Reminder',
    message_recipient=['Me'],      # person labels, or True for everyone. An empty list, None or False: nobody
    also_if_not_home=False,
    data={'tag': 'window'},        # Companion app notification data
)
# Sending message='clear_notification' with the same tag clears it on the phone. It is only sent to mobile_app_ receivers.
```

**Siri / iOS Shortcuts.** In the Shortcuts app add Home Assistant, Fire Event, event name `ios.lightwand-mode-change` (or your `ios_event`) and event data `{"message":"food"}`. When `siri_message` is configured, the matching entry sends its notification. Every received message is also re-fired as a `MODE_CHANGE` event, which is how Lightwand and ModeManagement receive mode changes from Shortcuts.

**Email.** Set up the SMTP integration in Home Assistant (Settings, Devices & services). It creates a notify entity for each email address you add. Use these entities as receivers of a recipient with `send_via: email`:

```yaml
  recipients:
    - person: Mail
      receiver:
        - notify.my_email        # "notify." is added if you leave it out
      send_via: email
```

The message is sent with `smtp.send_message`. Put `html`, `attachments` or `priority` in the `data` of `send_notification()` to use them. Do not put SMTP passwords in `apps.yaml`; `email_config` is not used. Older setups with a legacy `notify.<name>` SMTP service can keep it as a normal receiver without `send_via`, but Home Assistant has deprecated that service.

---

### Doors, windows and weather

#### door_guard

Reminds you when a door or window sensor has stayed open. The reminder repeats every `duration` seconds. The notification is cleared when all the sensors are closed, and with several sensors the reminders go on while any of them is open. The notification has a "Do not remind me" button.

```yaml
front_door_guard:
  module: door_guard
  class: DoorGuard
  dependencies:
    - notify_mobiles
  sensors:
    - sensor: binary_sensor.front_door
      duration: 300
  notify_receiver:
    - Me
  notify_title: 'Front door'
  notify_message: 'The {sensor} is open'
```

| Key | Required | Default | Description |
|---|---|---|---|
| `sensors` | **Yes** | | List of `sensor` (entity, `on` means open) and `duration` (seconds, default 300). A sensor that is open when AppDaemon starts is checked after its `duration`. |
| `notify_receiver` | **Yes** | | Person labels in `notify_mobiles`. |
| `notify_title` | **Yes** | | Notification title. |
| `notify_message` | **Yes** | | Notification text. `{sensor}` is replaced with the friendly name of the sensor that is open. |
| `also_if_not_home` | No | `false` | Set `true` to also notify people who are away, for example for a freezer door. |

Recipients who are not home are skipped unless `also_if_not_home` is `true`. When the sensors are closed, or you press the button, the notification is cleared on every phone.

#### bathroomWindow

Reminds you to close bathroom doors and windows once the humidity has dropped back to normal. A sensor must be open for `duration` seconds, the outdoor temperature must be at or below `check_below_temp` (from the ad-Weather `WEATHER_CHANGE` event), and the humidity must be at or below the median of the last `humidity_samples` readings plus `offset`. The reminder repeats every `duration` seconds until the window is closed or you press "Do not remind me". People who are not home are skipped.

```yaml
bathroom_window:
  module: bathroomWindow
  class: BathroomWindow
  dependencies:
    - notify_mobiles
  sensors:
    - sensor: binary_sensor.bathroom_window
      duration: 1200
  humidity: sensor.bathroom_humidity
  offset: 5
  check_below_temp: 20
  notify_receiver:
    - Me
  notify_title: 'Bathroom window open'
  notify_message: 'Humidity is down to normal'
```

| Key | Required | Default | Description |
|---|---|---|---|
| `sensors` | **Yes** | | List of `sensor` (entity, `on` means open) and `duration` (seconds, default 1200). A window that is open when the app starts is checked after its `duration`. |
| `humidity` | No | none | Humidity sensor. Without it the reminder is sent when a window has been open for `duration`. While its value is not known the humidity counts as normal. |
| `offset` | No | `5` | Allowed humidity above the median. |
| `humidity_samples` | No | `500` | Number of readings the median is taken from (the normal level follows the last readings, so spikes from a shower do not move it). Lost on reload. |
| `check_below_temp` | No | `20` | Only notify at or below this outdoor temperature. Without ad-Weather the temperature is not checked. |
| `notify_receiver` | **Yes** | | Person labels. |
| `notify_title` | No | `Bathroom Window Open` | |
| `notify_message` | No | `Humidity is down to normal` | |

Uses [ad-Weather](https://github.com/Pythm/ad-Weather) for the outdoor temperature when it is installed. When the windows are closed, or you press the button, the notification is cleared on every phone, also for people who have left since.

#### simultaneousOpened

Alerts only when a primary sensor (usually a window) and a second sensor (usually a door) are open at the same time. Optionally turns an `input_boolean` on while both are open, so other apps can react.

```yaml
window_and_door:
  module: simultaneousOpened
  class: SimultaneousOpen
  dependencies:
    - notify_mobiles
  sensors:
    - sensor: binary_sensor.living_room_window
      duration: 300
  simultaneous_sensor: binary_sensor.terrace_door
  simultaneous_switch: input_boolean.window_and_door
  temperature_sensor: sensor.outdoor_temperature
  check_below_temp: 23
  climate: climate.living_room
  notify_receiver:
    - Me
```

| Key | Required | Default | Description |
|---|---|---|---|
| `sensors` | **Yes** | | List of `sensor` and `duration` (seconds). A main sensor has to be open for at least 71 seconds, a lower value is raised to 71. |
| `simultaneous_sensor` | **Yes** | | The second sensor. |
| `simultaneous_delay` | No | `60` | Seconds the second sensor has to be open when it is opened after the main sensor. |
| `simultaneous_switch` | No | none | `input_boolean` that is on while both are open. |
| `temperature_sensor` | No | none | Alert only when the temperature is at or below `check_below_temp`. Use the sensor you want to react to, for example outdoor. An unknown value counts as cold enough. |
| `check_below_temp` | No | `23` | Temperature limit. |
| `climate` | No | none | No notification while this entity is `off` or `fan_only`. |
| `notify_receiver` | No | everyone | Person labels. If not set, everyone in `notify_mobiles` is notified. |
| `notify_title` / `notify_message` | No | `Both door and window is open` / `Close either` | |
| `also_if_not_home` | No | `false` | Set `true` to also notify people who are away. |

How it works: when a main sensor has been open for its `duration`, the notification is sent if the second sensor is open too. If it is closed, the app waits for it to be open for `simultaneous_delay` seconds. The notification is always checked against the sensors at that moment, so it is only sent when a main sensor and the second sensor are open together. The waiting continues until all the main sensors are closed, so opening the second sensor again gives a new notification. The switch also turns on when the temperature or climate filter suppresses the notification, and off, with the notification cleared on every phone, as soon as one of the two is closed. A sensor that is open when AppDaemon starts is checked after its `duration`.

#### rain_notify

Notifies when it rains, when it is windy, or when it is dark, while one of your window sensors is open. It listens to the `WEATHER_CHANGE` event from [ad-Weather](https://github.com/Pythm/ad-Weather). At most one notification of any kind is sent every `notify_interval` seconds (3 hours), so while the condition lasts, for example rain or darkness with a window still open, you are reminded every 3 hours until you close it. Recipients who are not home are skipped unless `also_if_not_home` is `true`.

```yaml
rain_notify:
  module: rain_notify
  class: Rain_Notify
  dependencies:
    - notify_mobiles
  notify_receiver:
    - Me
  windowsensors:
    - binary_sensor.window_kitchen
    - binary_sensor.window_bedroom
  rain_amount: 0.1
  anemometer_speed: 40
  lux_level: 900
```

| Key | Required | Default | Description |
|---|---|---|---|
| `windowsensors` | **Yes** | | A sensor or a list of them (`on` means open). Any entity that is `on` works, for example an `input_boolean` for laundry that is outside. |
| `notify_receiver` | **Yes** | | Person labels. |
| `rain_amount` | No | `0.1` | Rain threshold, in the unit your ad-Weather sensor reports. |
| `anemometer_speed` | No | `40` | Wind threshold, in the unit your ad-Weather sensor reports. |
| `lux_level` | No | none | Notify when lux is below this value. |
| `notify_interval` | No | `10800` | Seconds before another notification can be sent. Shared by rain, wind and lux. |
| `also_if_not_home` | No | `false` | Set `true` to also notify people who are away. |
| `rain_title` / `wind_title` / `lux_title` | No | `Rain` / `Wind` / `Lux` | |
| `rain_message` / `wind_message` / `lux_message` | No | `It's raining and {windows} is open` / `It's windy and {windows} is open` / `It's getting dark and {windows} needs attention` | `{windows}` is replaced with the friendly names of the sensors that are on, separated by commas. |

Rain is checked first, then wind, then lux, and only one notification is sent for each weather event. A weather event without a number for rain, wind or lux is ignored for that check.

#### garagedoor

Opens a garage cover when a person arrives home, and warns, with a photo and a "Close" button, when the house goes to night or away mode with the garage not closed.

> [!WARNING]
> This app can open a door automatically. Use a `switch` for every person so that the door only opens when you have armed it, and test with your own presence detection first.

```yaml
garage_door:
  module: garagedoor
  class: GarageDoor
  dependencies:
    - notify_mobiles
  garage: cover.garage_door
  notify_receiver:
    - Me
  auto_open:
    - presence: person.me
      switch: input_boolean.auto_open_garage
  camera: camera.garage
  target_directory: /config/www/snapshots/
```

| Key | Required | Default | Description |
|---|---|---|---|
| `garage` | **Yes** | | `cover` entity. |
| `notify_receiver` | **Yes** | | Person labels. |
| `auto_open` | No | none | **List** of items with `presence` (**required**, a `person` or tracker) and `switch` (optional `input_boolean`). An item without `presence` is ignored with an ERROR. |
| `camera` | No | none | Camera for the notification photo. |
| `target_directory` | No | `www/snapshots/` | Snapshot folder. The path must contain a `www` segment, exist for Home Assistant, and be in Home Assistant's `allowlist_external_dirs`. |
| `snapshot_keep_days` | No | none | Delete snapshots (`image_*.jpg`) in `target_directory` older than this many days after each new snapshot. Without it nothing is ever deleted. Applies to every snapshot in that folder, also from other apps. Files in `www` are served at `/local/` without login. |

**Auto-open.** With a `switch`, turning the switch on arms the door for that person. When the person arrives home (the state changes to `home` from `not_home` or a zone), the garage is opened and the switch is turned off, so it has to be turned on again for the next arrival. Arrival from `unavailable` or `unknown`, for example after a restart of Home Assistant or the tracker, does not open the door. Without a `switch` the item is armed when AppDaemon starts and opens the door once; it is armed again only when the app reloads, so use a switch.

**Warning.** On a `MODE_CHANGE` event with the night or away mode, a notification with a "Close" button is sent to `notify_receiver`, also to people who are away, if the garage state is not `closed` or `closing`. Mode names come from [ad-Lightwand](https://github.com/Pythm/ad-Lightwand) when it is installed, otherwise English (see [Mode names](#mode-names)).

#### doorbell

Sends a notification with a camera snapshot when a doorbell entity turns `on`, then optionally shows the camera stream on media players. Optionally sets a chime volume by time of day.

```yaml
doorbell:
  module: doorbell
  class: Doorbell
  dependencies:
    - notify_mobiles
  doorbell: binary_sensor.front_door_ring
  notify_receiver:
    - Me
  camera: camera.front_door
  target_directory: /config/www/snapshots/
  media_player:
    - media_player.living_room_tv
  chime: number.doorbell_chime_volume
  daytime_volume: 80
  nighttime_volume: 30
  daytime_start: '06:00:00'
  daytime_stop: '22:00:00'
```

| Key | Required | Default | Description |
|---|---|---|---|
| `doorbell` | **Yes** | | Entity that turns `on` when pressed. An `event.*` entity also works: every change of its state counts as a ring. |
| `notify_receiver` | **Yes** | | Person labels. |
| `notify_title` | No | `Home Assistant` | |
| `notify_message` | No | `Someone at the door` | |
| `notify_when_away` | No | `true` | Notify people who are not home. |
| `camera` | No | none | Without a camera there is no snapshot and no stream. |
| `target_directory` | No | `www/snapshots/` | As for `garagedoor`: must contain `www`, be a path Home Assistant can write, and be allowlisted. |
| `snapshot_keep_days` | No | none | As for `garagedoor`. |
| `media_player` | No | none | Media player, or a list. A player that is `playing` is stopped, then every player that is not `off`, `standby`, `unavailable` or `unknown` receives `camera/play_stream`. |
| `chime` | No | none | A `number` or `input_number` entity. |
| `daytime_volume` / `nighttime_volume` | No | `80` / `30` | |
| `daytime_start` / `daytime_stop` | No | `06:00:00` / `22:00:00` | When the chime volume changes. It is also set when the app starts. |

The notification is sent first, before the stream is started, so a problem with a media player cannot stop it. Every ring takes a new snapshot and sends a new notification.

---

### Presence and vacation

#### end_vacation

Turns off vacation switches when a person returns home, or at a planned date and time. The "return home" detection is armed after a vacation switch has been on for `arm_delay` seconds (2 hours by default), so leaving the house does not end the vacation. The first person to arrive ends it for everyone. It works for every vacation, also after a restart of AppDaemon in the middle of one.

```yaml
vacation_end:
  module: end_vacation
  class: endVacation
  vacation_switch:
    - input_boolean.vacation
  presence:
    - person.me
  vacation_ends: input_datetime.vacation_ending
```

| Key | Required | Default | Description |
|---|---|---|---|
| `vacation_switch` | **Yes** | | `input_boolean` (or a list of them). All are turned off when the vacation ends. |
| `presence` | No | none | `person` or tracker entity, or a list. Without it only `vacation_ends` is used. |
| `vacation_ends` | No | none | `input_datetime` with date **and** time (a date alone means 00:00). Changes to it are picked up after 60 seconds. A time in the past or an empty value plans nothing. |
| `arm_delay` | No | `7200` | Seconds a vacation switch has to be on before arrival at home ends the vacation. |

If AppDaemon is down when `vacation_ends` passes, the switches are not turned off after it starts again.

#### wake_up

Morning routine: plays a playlist, then turns on lights, only when the alarm is active. The alarm is active when vacation is off, the switch for the kind of day is on (`alarm_switch` on a workday, `alarm_switch_non_work_day` on a holiday or weekend) and all `conditions` are true. Music and lights follow the same rule. A time of `00:00:00` disables it.

```yaml
wake_up_alarm:
  module: wake_up
  class: WakeUp
  time: input_datetime.wakeup               # time only, not date+time
  media_player: media_player.bedroom
  playlist: 'Playlists/Morning'
  volume: 0.2
  country_code: 'NO'                        # optional, public holidays count as non-work days
  vacation: input_boolean.vacation
  alarm_switch: input_boolean.alarm_workday
  alarm_switch_non_work_day: input_boolean.alarm_holiday
  wake_up_lights:
    - light.bedroom_light
  light_time_offset: 5
```

| Key | Required | Default | Description |
|---|---|---|---|
| `time` | **Yes** | none | Time-only `input_datetime`. `00:00:00` turns the alarm off. A value that is not a time (`unknown`, `unavailable`) leaves the current plan as it was. |
| `media_player` | **Yes** | | Entity or list. Played with content type `music`. |
| `playlist` | **Yes** | | Media id for the player. |
| `volume` | No | none | 0.0 to 1.0. |
| `wake_up_lights` | No | `[]` | HA light entities. |
| `wake_up_MQTTlights` | No | `[]` | Base MQTT topics, publishes to `<topic>/set` (zigbee2mqtt convention) with `"state": "ON"` added to `light_data`. |
| `light_data` | No | `{}` | Payload for the lights, for example `brightness` or `effect`. The same data goes to `wake_up_lights` and the MQTT lights. |
| `light_time_offset` | No | `0` | Minutes after (or before, if negative) the music. An offset that crosses midnight checks the day at the time the lights come on. |
| `vacation` | No | `input_boolean.vacation` | Alarm is off while on. |
| `alarm_switch` / `alarm_switch_non_work_day` | No | `input_boolean.alarm_switch` / `input_boolean.alarm_switch_non_work_day` | Set both explicitly. The first is for workdays, the second for holidays and weekends. |
| `country_code` | No | none | ISO code for the `holidays` library. With it, public holidays count as non-work days, like weekends. Without it, or with an unknown code (a WARNING is logged), only weekends do. Nothing is looked up or sent anywhere. |
| `conditions` | No | `[]` | List of Python expressions evaluated with `eval`. See below. |
| `MQTT_namespace` | No | `mqtt` | Namespace of the MQTT plugin. |

**Conditions** are Python strings evaluated by the app. Only put your own text there. In this app the Home Assistant calls are on `self.ADapi`:

```yaml
conditions:
  - "self.ADapi.get_state('person.partner') == 'home'"
```

Examples that use `self.get_state(...)` or `self.get_tracker_state(...)` fail in this app. A condition that raises an error is logged as an ERROR and the alarm does not go off.

Needs the `holidays` package. For the AppDaemon add-on, list them in `python_packages` (see the [ModeManagement note](https://github.com/Pythm/ad-ModeManagement/issues/15#issuecomment-3688156477)).

**Note:** the content type of the playlist is always `music`.

---

### Appliances and energy

#### appliance_notify

Sends a notification when a power sensor shows that a program has finished: the power has been above `start_threshold` (100 W) for `start_duration` (30 s), and then below `stop_threshold` (15 W) for `stop_duration` (30 s). The sensor must report watts. Every new reading is checked, so a sensor that changes often works. Optionally switches the appliance off inside a time window (to stop beeping) and back on 60 seconds later.

```yaml
tumble_dryer:
  module: appliance_notify
  class: Dryer
  dependencies:
    - notify_mobiles
  dryer_power: sensor.tumble_dryer_power
  dryer_switch: switch.tumble_dryer
  notify_receiver:
    - Me
  notify_title: 'Tumble dryer'
  notify_message: 'The dryer has finished'
  turn_off_after: '22:00:00'
  turn_off_before: '07:00:00'
```

| Key | Required | Default | Description |
|---|---|---|---|
| `dryer_power` | **Yes** | | Power sensor in W. |
| `notify_receiver` | **Yes** | | Person labels. |
| `notify_title` / `notify_message` | No | `Tumbledryer` / `Tumbledryer is finished` | |
| `start_threshold` / `stop_threshold` | No | `100` / `15` | Watts. Raise `stop_duration` for appliances with long low-power phases, otherwise they give false "finished" messages. |
| `start_duration` / `stop_duration` | No | `30` / `30` | Seconds the power has to stay above / below the threshold. |
| `dryer_switch` | No | none | A switch-like entity (`switch`, `input_boolean`, `light`). Adds a "Turn Off" button. |
| `turn_off_after` / `turn_off_before` | No | `22:00:00` / `07:00:00` | Window for the automatic turn-off. Used only with `dryer_switch`. |
| `turn_back_on_after` | No | `60` | Seconds until the switch is turned on again after the app turned it off. `0` never turns it back on. Used only with `dryer_switch`. |

Whenever the app turns the switch off (button or window), it turns it back **on** after `turn_back_on_after` seconds. If you switch it off yourself, nothing is turned back on.

While the sensor is `unavailable` or `unknown` no notification is sent. If AppDaemon restarts during a program, the app picks up that it is running. The "Turn Off" button and `destructive` icon use iOS notification options.

#### appliance_home_connect

Starts a Home Connect appliance (written for a dishwasher) at the cheapest time, using [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc). You press remote start on the appliance, the app picks the start time and selects the program.

> [!WARNING]
> Starts an appliance unattended. With `run_during_nightmode` it runs while you sleep. Use at your own risk.

```yaml
dishwasher:
  module: appliance_home_connect
  class: HomeConnect
  dependencies:
    - electricalPriceCalc
    - notify_mobiles
  notify_receiver:
    - Me
  remote_start: binary_sensor.dishwasher_remote_start
  active_program: select.dishwasher_active_program
  vacation: input_boolean.vacation
  day:
    program: dishcare_dishwasher_program_eco_50
    running_time: 3          # hours
    finish_by: 16            # hour of day
  night:
    program: dishcare_dishwasher_program_night_wash
    running_time: 4
    finish_by: 7
  options:
    - run_during_nightmode
    - run_during_awaymode
```

| Key | Required | Default | Description |
|---|---|---|---|
| `remote_start` | **Yes** | | Entity that is `on` when the appliance is armed for remote start. |
| `active_program` | **Yes** | | The Home Connect `select` entity for the program. |
| `notify_receiver` | **Yes** | | Person labels. |
| `day`, `night` | At least one | none | Each: `program` (**required**), `running_time` in hours (day 3, night 4), `finish_by` hour (day 16, night 7). If only one is given it is used for both. |
| `options` | No | none | `run_during_nightmode`: schedule when night mode is activated. `run_during_awaymode`: schedule when away mode is activated. With an option set, a remote start in that situation waits for the mode event. |
| `vacation` | No | `input_boolean.vacation` | Blocks the actual start while on. Scheduling and notifications still happen. |
| `price_app` | No | `electricalPriceCalc` | Name of the ElectricalPriceCalc app. |

How the day or night program is chosen: from `night.finish_by - night.running_time` up to `day.finish_by - day.running_time` (03:00 to 13:00 with the values above) the day program is used, otherwise the night program. Notification buttons let you start either program immediately. With `run_during_nightmode` or `run_during_awaymode` set, a remote start waits for that mode, unless the house is already in it (the app tracks the house mode from `MODE_CHANGE` events since it started). The app only schedules when you press remote start (`off` to `on`) or when a mode event arrives with remote start on; it does not schedule at startup, because Home Connect keeps remote start on after a wash. If AppDaemon restarts while a start is waiting, press remote start again. If the price app has no start time yet (for example before tomorrow's prices are published), the app asks again every 30 minutes, up to 6 times, then sends a notification and does not start. Mode names and the `MODE_CHANGE` event come from `ad-Lightwand` when it is installed, otherwise English.

**Note:** when vacation turns off, the day program is scheduled whatever the time of day, also if remote start is off.

#### espresso_machine

Turns a switch (coffee machine) on at the time set in an `input_datetime`, and sends a "still on" notification at `last_chance` with a "Turn Off" button. The reminder is also sent when you are away.

> [!WARNING]
> Turns on a heating appliance unattended.

```yaml
espresso:
  module: espresso_machine
  class: EspressoMachine
  dependencies:
    - notify_mobiles
  espresso_machine: switch.espresso
  coffee_timer: input_datetime.espresso_on
  vacation: input_boolean.vacation
  last_chance: '15:00:00'
  notify_receiver:
    - Me
  notify_title: 'Coffee'
  notify_message: 'Coffee machine is still on'
```

| Key | Required | Default | Description |
|---|---|---|---|
| `espresso_machine` | **Yes** | | Switch-like entity (`switch`, `input_boolean`, `light`, `fan`). |
| `notify_receiver` | **Yes** | | Person labels. |
| `coffee_timer` | No | none | Time-only `input_datetime` (a date and time works too, the date is ignored). `00:00:00` disables the automatic start. A value that is not a time (`unknown`, `unavailable`) leaves the plan as it was. Without `coffee_timer` only the reminder works. |
| `vacation` | No | `input_boolean.vacation` | No automatic start while on. |
| `last_chance` | No | `15:00:00` | Time of the reminder. |
| `notify_title` / `notify_message` | No | `Coffee` / `Coffee machine is still on` | |

The machine is only turned on if it is `off`. Without the notify app (an ERROR is logged) the machine is still turned on, but no reminder is sent. An AppDaemon `constrain_days` (for example to skip weekends) affects the whole app, so it also suppresses the safety reminder.

#### log_energy_usage

Logs energy use and cost to files, per day and per month, using the prices from [ElectricalPriceCalc](https://github.com/Pythm/ElectricalPriceCalc). The sensors must be **cumulative kWh** meters. Cost = consumption in each price period x price. Optional guest-usage tracking and a monthly cost text in an `input_text`.

```yaml
log_energy_usage:
  module: log_energy_usage
  class: LogEnergyUsage
  dependencies:
    - electricalPriceCalc
    - notify_mobiles
  notify_receiver:
    - Me
  csv_folder_path: /conf/db/
  items:
    - name: Total                       # special name: gives the average price
      entity: sensor.home_energy_total_kwh
    - name: Car charger
      entity: sensor.charger_lifetime_energy
      input_text: input_text.charger_cost_this_month
      guestUse: input_boolean.guest_charging
```

| Key | Required | Default | Description |
|---|---|---|---|
| `items` | **Yes** | | List of items, see below. |
| `notify_receiver` | **Yes** | | Person labels (for guest-cost notifications). The app fails to start without it. |
| `csv_folder_path` | No | `/conf/db/` | Writable folder. It is created if it does not exist. |
| `electricalPriceApp` | No | `electricalPriceCalc` | Name of the price app. |
| `max_kw` | No | `100` | The most power a sensor can plausibly show. A reading that moves more than `max_kw` times the hours since the last good reading is not trusted, see below. Can be set per item too. |
| `items[].name` | **Yes** | | `Total` is special: it gives the average monthly price. |
| `items[].entity` | **Yes** | | Cumulative kWh sensor. |
| `items[].namespace` | No | `HASS_namespace` | Namespace of the sensor. |
| `items[].max_kw` | No | `max_kw` | |
| `items[].input_text` | No | none | Receives the monthly cost text. |
| `items[].namespace_input_text` | No | `HASS_namespace` | |
| `items[].guestUse` | No | none | `input_boolean`. While on, the usage is logged in a separate guest column, and the guest cost is sent as a notification when it turns off. |
| `items[].guest_name` | No | `<name>Guest` | Name of the guest column. |
| `items[].namespace_guest` | No | `HASS_namespace` | |

Files written to `csv_folder_path` (tab-separated, despite the `.csv` extension): `daily_tmp_storage.json` (state), `every_day_cost_usage.csv`, `total_energy_usage.csv`, `monthly_energy_usage.csv` and `monthly_cost_usage.csv`. The state is saved after every price period, so a crash loses at most one period. The first month has no useful monthly values.

**Guest usage.** An item with `guestUse` gets a second column right after it, for example `Easee` and `EaseeGuest`, in all four files. While `guestUse` is on, and for the period in which it turns off, the usage goes to the guest column and is left out of the item's own column, so the two add up to what the sensor measured. The meter snapshot file (`total_energy_usage.csv`) holds the sensor reading in the item column and a running guest kWh counter in the guest column. The monthly `input_text` of the item shows the item's own cost without the guest part. The first time an item gets a guest column, the files are updated as described below and the old rows keep an empty guest column. Do not use `guestUse` on the `Total` item.

**Changing `items`.** When you add, remove or reorder items, the header of each file is updated the next time the app writes to it. Values are kept by column name, new columns are empty, columns of removed items are dropped, and the old file is saved next to it as `.bak`.

**Sensors that report strange values.** Each reading is compared with the last trusted one.
- A change within what `max_kw` allows is used, also a negative one (net metering with solar).
- A larger jump is not used at once. If the next reading is back near the old value it was a glitch and is dropped. If the next reading stays at the new level, the sensor really changed: after a reset to zero the new value counts as consumption, after anything else (a replaced meter) the jump counts as no consumption. A WARNING is logged.
- A sensor that is `unavailable` at startup starts logging when it becomes available. No restart needed.

**Known limits:** if AppDaemon is down at 00:01 on the 1st, the summary for that month is not written. Downtime across midnight merges the days into one row. Consumption while AppDaemon was down is charged at the price of the first period after it started.

#### charger_controller

Keeps a rechargeable device from sitting at full charge. It turns the charger switch off at `max_level` (80 %) when the device is home, and on again at `min_level` (75 %). It reacts when the battery sensors update and also checks every `check_interval` seconds (15 minutes) in case they do not.

```yaml
ipad_charger:
  module: charger_controller
  class: MobileChargerController
  charger_switch: switch.ipad_charger_plug
  battery_state: sensor.ipad_battery_state
  battery_level: sensor.ipad_battery_level
  device_location: device_tracker.ipad
```

| Key | Required | Default | Description |
|---|---|---|---|
| `charger_switch` | **Yes** | | Switch-like entity (`switch`, `input_boolean`, `light`) for the charger socket. Do not share the socket with other devices. |
| `battery_state` | **Yes** | | Companion app battery state sensor. iOS (`Charging`, `Full`, `Not Charging`) and Android (`charging`, `full`, `not_charging`) are both understood. |
| `battery_level` | **Yes** | | Battery percent. While it is `unavailable` or `unknown` nothing happens. |
| `device_location` | No | none | Tracker; turn-off only happens when it is `home`. Turn-on does not check it. |
| `max_level` / `min_level` | No | `80` / `75` | Percent. |
| `check_interval` | No | `900` | Seconds between the regular checks. The first one runs 3 minutes after start. |

The companion app only updates the sensors now and then. On iOS you can make them update at the thresholds with a Shortcuts personal automation: trigger **Battery Level**, level 80 and "Rises above", run immediately, action Home Assistant **Update Sensors**. Repeat for 75 and "Falls below".

---

### Media

#### media_pause

Pauses media players when every presence sensor has been `off` for `pause_delay` seconds (60) and resumes the players it paused when a sensor turns `on`. Use AppDaemon's built-in `constrain_start_time` and `constrain_end_time` to limit when it runs.

```yaml
pause_when_empty:
  module: media_pause
  class: MediaPause
  sensors:
    - binary_sensor.room_presence
  media_player:
    - media_player.living_room
  constrain_start_time: '07:30:00'
  constrain_end_time: '20:00:00'
```

| Key | Required | Default | Description |
|---|---|---|---|
| `media_player` | **Yes** | | Media player, or a list. |
| `sensors` | **Yes** | none | Presence sensor, or a list. The pause only happens when none of them is `on`. |
| `pause_delay` | No | `60` | Seconds all sensors have to be `off`. |
| `resume_within` | No | `14400` | A pause older than this many seconds (4 hours) is not resumed, so music paused yesterday evening does not restart the next morning. |

Only players that were playing (not `off`, `standby`, `idle`, `paused`, `unavailable` or `unknown`) are paused, and only the players this app paused are resumed, so a player you paused yourself stays paused. Note that the time constraints apply to the whole app, also to the resume.

#### media_stop

Stops media players when a sensor turns `on` (for example a doorbell or door sensor).

```yaml
stop_media:
  module: media_stop
  class: MediaStop
  sensors:
    - binary_sensor.front_door_ring
  media_player:
    - media_player.living_room_tv
  activate_switch: input_boolean.enable_media_stop    # optional
```

| Key | Required | Default | Description |
|---|---|---|---|
| `media_player` | **Yes** | | Media player, or a list. Entity ids are lowercase. |
| `sensors` | **Yes** | none | Trigger sensor, or a list. |
| `activate_switch` | No | none | Only listen to the sensors while this entity is on. Turning it on arms the sensors, turning it off disarms them, and it is armed at start if it is already on. |

Every player that is not `off`, `standby`, `idle`, `unavailable` or `unknown` is stopped, which includes players that are `paused`, `on` or `buffering`.

---

### Safety

#### fire_alarm

Reacts to smoke detectors: fires a `MODE_CHANGE` event with the fire mode (so [ad-Lightwand](https://github.com/Pythm/ad-Lightwand), [ad-ClimateCommander](https://github.com/Pythm/ad-ClimateCommander), [ad-ElectricalManagement](https://github.com/Pythm/ad-ElectricalManagement) and [ad-ModeManagement](https://github.com/Pythm/ad-ModeManagement) can react), sends a notification, also to people who are away, then turns off listed devices and opens listed covers.

> [!WARNING]
> Not a certified safety system. Test it with your own detectors before relying on it. Opening garage doors or screens during a fire is a decision you should make deliberately.

```yaml
firealarm:
  module: fire_alarm
  class: FireAlarm
  dependencies:
    - notify_mobiles
  notify_receiver:
    - Me
  alarms:
    - binary_sensor.zone_1_smoke
  turn_off:
    - switch.dishwasher_power
  screens:
    - cover.living_room_screen
  modeManagementApp: manageModes           # optional
```

| Key | Required | Default | Description |
|---|---|---|---|
| `alarms` | **Yes** | | Smoke `binary_sensor`, or a list of them. |
| `notify_receiver` | **Yes** | | Person labels. |
| `turn_off` | No | none | Entity, or a list, to turn off. Everything that is not already `off`, `unavailable`, `unknown` or `standby` is turned off, also a media player that is `playing`. |
| `turn_off_media_players` | No | `true` | Also turn off every `media_player` that exists when the alarm goes off. Set `false` to only use `turn_off`. |
| `screens` | No | none | Cover, or a list, to open when someone is home. A cover is opened unless its `current_position` is 100. |
| `modeManagementApp` | No | none | ModeManagement app name used for "anyone home". Without it, or if the app is not found (a WARNING is logged), someone is assumed to be home. |

The notification names the detector by its friendly name and is sent before the devices are turned off. Without the notify app (an ERROR is logged) the rest still works.

**When the fire mode ends.** The `false_alarm` mode is fired when a detector returns to `off` and no detector is `on` any more, also when it went `on`, `unavailable`, `off`. A fire that is going on when AppDaemon starts is ended the same way. The mode names come from Lightwand's `translations.json` when Lightwand is installed, otherwise the English defaults are used (see [Mode names](#mode-names)).

---

### Network

#### change_dns_cloudflare

Keeps a Cloudflare DNS `A` record equal to your public IP. The IP comes from a Home Assistant sensor (`ip_sensor`, updated when the sensor changes). Without a sensor the app asks an IP service at startup and at 10 minutes past every hour; by default `https://api.ipify.org`, which sees your IP address. At startup the app also compares the record with the public IP and updates it if they differ, for example after an IP change while AppDaemon was down.

```yaml
update_cloudflare_dns:
  module: change_dns_cloudflare
  class: Change_DNS
  cloudflare_api_token: !secret cloudflare_token
  zone_id: !secret cloudflare_zone_id
  dns_record_id: !secret cloudflare_record_id
  ip_sensor: sensor.my_public_ip
```

| Key | Required | Default | Description |
|---|---|---|---|
| `cloudflare_api_token` | **Yes** | | API token with Zone.DNS Edit permission for this zone only (My Profile, API Tokens). Store it in `secrets.yaml`. |
| `zone_id` | **Yes** | | On the zone's Overview page in the Cloudflare dashboard. |
| `dns_record_id` | **Yes** | | List records via the API: `GET https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records`. |
| `ip_sensor` | No | none | HA sensor with the public IPv4 address. Without it the IP service is used. |
| `ip_check_url` | No | `https://api.ipify.org` | Any service that returns your IPv4 address as plain text. Only used without `ip_sensor`. |
| `enable_proxy` | No | keep the record's setting | `true` or `false` sets Cloudflare proxying on every update. Not set: the proxy setting you have in Cloudflare is left alone. Proxying breaks VPN, SSH, MQTT and other non-HTTP use. |

Only the IP (`content`) is changed, so TTL and comment stay. Only IPv4 `A` records are supported: the app refuses a record of another type, and ignores a sensor value that is not an IPv4 address or is `unavailable`. A failed update is tried again after 15 minutes, up to 6 times, and then at the next trigger. Use one app section for each record.

---

## Troubleshooting

- **AppDaemon starts no app after I changed `dependencies`:** a name in `dependencies` is not an app in your configuration. Fix the name or remove the line.
- **ERROR "Could not find app ...":** the notify app (or the price app) was not loaded when the app started. Check the name (`notify_app`, `price_app`) and add it to `dependencies`.
- **KeyError for `notify_receiver` or another key on start:** a required key is missing, see the table of the app.
- **Nothing happens and nothing is logged:** set `log_level: DEBUG` in the app's section, check the entity ids, and the namespace if you have more than one Home Assistant.
- **Mode names are English although I translated them:** see [Mode names](#mode-names) and add `dependencies: mode_translation`.
- **Snapshot notification has no image:** the target directory must be writable by Home Assistant, contain a `www` segment and be in `allowlist_external_dirs`.

## Contributing and support

Issues and pull requests are welcome on [GitHub](https://github.com/Pythm/Pythm_AppdaemonApps). Please include the app name, your `apps.yaml` section (with secrets removed) and the relevant log lines.

If these apps are useful to you, you can [buy me a coffee](https://www.buymeacoffee.com/pythm).

## License

MIT, see [LICENSE](LICENSE). The apps are provided as-is, without warranty. You are responsible for what they switch on and off in your home.
