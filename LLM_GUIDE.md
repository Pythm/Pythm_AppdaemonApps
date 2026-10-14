# Set up Pythm's apps with an AI assistant

This guide lets an AI assistant (Claude Code, Codex, or any assistant that can read and edit files in this folder) write your `apps.yaml` using the **real entity names from your own Home Assistant**, so you do not have to hunt for them or guess.

It has two parts: a short one for **you**, and rules for **the assistant**. You do not need to know YAML or Python.

> [!IMPORTANT]
> The apps control real things: doors, heaters, appliances and a smoke-alarm reaction. The assistant must explain what an app will do and get a clear "yes" from you before it is added.

## What you do (about 10 minutes)

1. Open this repository folder in your AI assistant.
2. Say something like: *"Read LLM_GUIDE.md and help me set up the Pythm apps for my home. I want door reminders and a notification when the dryer is done."*
3. When the assistant asks, create the access token (Step 1) and paste it into the file the assistant points you to (Step 2). **Never paste the token into the chat.**
4. Answer the assistant's questions, for example which of two matching sensors is your front door.
5. When it is done, delete the token again (last section).

---

## Step 1: Create a long-lived access token (you)

A token lets the script read your Home Assistant, like a password that only works for programs.

1. Open Home Assistant in your browser and log in.
2. Click your **name at the bottom of the left sidebar** to open your profile.
3. Open the **Security** tab and scroll to the bottom, to **Long-lived access tokens**.
4. Click **Create token**, name it `AI assistant`, and click **OK**.
5. **Copy the token now.** Home Assistant shows it only once. If you lose it, create a new one.

Notes:

- The token gives full access to Home Assistant, as if it were you. Treat it like a password and delete it when you are done.
- Use an **administrator** account. Without admin the script still works, but it cannot see which room (area), device or integration an entity belongs to, so matches are less precise.

## Step 2: Save the token in the local file (assistant creates it, you fill it in)

**Assistant:** run this from the repository folder and tell the user the full path it prints:

```bash
python3 tools/ha_snapshot.py --init
```

It creates an empty file `.local/ha_token` and checks that git ignores the `.local` folder.

**You:**

1. Open the file `.local/ha_token` in a **plain text** editor (Notepad, VS Code, or on a Mac `open -e .local/ha_token`; TextEdit's default rich-text mode corrupts the token). The `.local` folder is hidden: on a Mac press Cmd+Shift+. in Finder to show it, on Windows turn on "Hidden items".
2. Paste the token on the **first line**, nothing else, no quotes. Save the file.
3. Tell the assistant "done". Do not paste the token into the chat.

Do not keep this repository in a folder that syncs to the cloud (iCloud Desktop/Documents, OneDrive, Dropbox), or the token is uploaded with it.

**Assistant:** never open, print or repeat the contents of `.local/ha_token`. The script reads it itself.

## Step 3: Read your entities (assistant)

Ask the user for the address they type to open Home Assistant, for example `http://homeassistant.local:8123` or `http://192.168.1.20:8123`. It must include the port (`:8123` unless changed). Then run:

```bash
python3 tools/ha_snapshot.py --url http://homeassistant.local:8123
```

It prints a summary and writes `.local/ha_index.jsonl`, one line per entity. The address is remembered, so later runs need no `--url`. Use `--insecure` only if the address is `https://` with a self-signed certificate. Run it again whenever the user adds devices.

What the script does: it **only reads** (entities, devices, rooms, current states, notify service names). It changes nothing in Home Assistant. It needs only Python 3.8 or newer, nothing to install.

What is in the index, and what is not: entity ids, names, rooms, integration, device class, unit, and the current state (cut at 40 characters). The state of `person`, `device_tracker` and `zone` entities and all GPS data are left out. There are no passwords or tokens in it.

---

## Rules for the assistant

1. **Entity ids come from the index, never from memory.** An id you did not find in `.local/ha_index.jsonl` does not go into the YAML. If several entities match (two door sensors, a sensor and its battery), show the user a short list with name and room and ask. If nothing matches, say so. Do not make an id up.
2. **Helpers do not exist until the user creates them.** `input_boolean`, `input_datetime`, `input_text` and `input_number` entities used by some apps are created in Settings, Devices & services, Helpers. If one is missing, tell the user exactly what to create (type and suggested name), then run the script again.
3. **Keys come from the README.** Read the section of the app in `README.md` for keys, required/optional and defaults. Do not invent keys.
4. **Read-only towards Home Assistant.** The token is for `tools/ha_snapshot.py` only. Do not use it for any other call, and never call a service or change a state unless the user asks for it in that message.
5. **Never read, print, store or repeat the token.** Not in chat, not in `apps.yaml`, not in `secrets.yaml`, not in logs or commit messages.
6. **Ask before editing `apps.yaml`.** Back it up first (copy to `apps.yaml.bak`), add **one app at a time**, show the user the block, and explain in one or two sentences what it will do. For apps that act on their own (`garagedoor`, `espresso_machine`, `appliance_home_connect`, `charger_controller`, `fire_alarm`) get an explicit yes.
7. **Start with `notify_mobiles`.** Most apps need it. Every app that notifies gets `dependencies: [notify_mobiles]` and a `notify_receiver` that matches a `person` label defined in `notify_mobiles`.
8. **Never add a name to `dependencies` that is not an app in `apps.yaml`.** AppDaemon then starts **no app at all**.
9. **Validate before telling the user it is done.** Parse the YAML, check every `dependencies` name exists as an app, check every entity id exists in the index, and check that required keys from the README are present. Then ask the user to look at the AppDaemon log for ERROR lines after a reload, or help them read it.
10. **No git actions without being asked.** Do not commit or push. `.local/` is ignored by git; if `git status` ever lists a file from it, stop and tell the user.
11. **Do not paste the index into the chat.** Search it (see below). It is large and it describes the user's home.

## Always ask the user how something is used

An entity that matches is not the same as the right entity for the job. Do not decide these from names, rooms or defaults, ask the user, and wait for the answer before writing the block:

- **Two sensors of one kind** (two outdoor lux or temperature sensors, two door sensors, two power meters): is the second a backup, a sensor for another side or room, or something else? The apps treat a list of sensors in one way (for example highest lux, lowest temperature, any open door), so the answer decides which app and which key gets each sensor.
- **Who gets notifications:** which person labels go in `notify_receiver`, and whether people who are away should be notified.
- **Apps that act on their own** (doors, heaters, chargers, the fire alarm): what exactly may they do, and should it be on from the start.
- **Thresholds and times** that depend on the home (rain limit, lux level, delays): suggest the README default and ask.
- **Sensors that report `unavailable` or `unknown` on purpose** (an alert app may be meant to fire when a sensor drops off): do not filter or "fix" this without asking.
- **A sensor from a helper, car or heat pump** that looks like it fits (for example an `Outside temperature` of a heat pump): ask before using it. It is often not the sensor the user means.
- **A second Home Assistant** (a `HASS_namespace` other than `default`): ask which entities live where.

Each app's own `LLM.md` (if the repository has one) lists more questions for that app.

## Searching the index

Each line is a JSON object. Fields: `entity_id`, `name`, `area` (room), `device`, `manufacturer`, `model`, `integration`, `device_class`, `unit_of_measurement`, `state_class`, `state`, `domain`, `kind` (`entity` or `notify_service`).

```bash
# Door and window sensors
grep -E '"device_class":"(door|window|opening|garage_door)"' .local/ha_index.jsonl

# Everything in one room
grep '"area":"Kitchen"' .local/ha_index.jsonl

# Power sensors measured in watts
grep '"device_class":"power"' .local/ha_index.jsonl | grep '"unit_of_measurement":"W"'

# Free text in the name (case-insensitive)
grep -i 'dryer' .local/ha_index.jsonl

# Notify services for phones (used in notify_mobiles)
grep '"kind":"notify_service"' .local/ha_index.jsonl | grep mobile_app
```

Without `grep`, use Python: `python3 -c "import json;[print(r['entity_id'],r.get('name'),r.get('area')) for r in map(json.loads,open('.local/ha_index.jsonl')) if r['domain']=='climate']"`.

## What to look for, per app

For each app, the keys below take Home Assistant entities. `on` on a `binary_sensor` normally means open, detected or active.

| App | Key | Look for |
|---|---|---|
| `notify_mobiles` | `receiver` | `kind` `notify_service` named `mobile_app_...` (one per phone with the Companion app). |
| `notify_mobiles` | `tracker` | `person.*` entities. |
| `door_guard`, `bathroomWindow`, `simultaneousOpened`, `rain_notify` | `sensor`, `simultaneous_sensor`, `windowsensors` | `binary_sensor` with `device_class` `door`, `window`, `opening` or `garage_door`. |
| `bathroomWindow` | `humidity` | `sensor` with `device_class` `humidity`, in the bathroom. |
| `simultaneousOpened` | `temperature_sensor`, `climate` | `sensor` with `device_class` `temperature` (outdoor is usual); a `climate.*` entity. |
| `simultaneousOpened` | `simultaneous_switch` | A helper `input_boolean` you create. |
| `garagedoor` | `garage` | `cover.*` with `device_class` `garage`. |
| `garagedoor` | `auto_open[].presence`, `switch` | `person.*`; one `input_boolean` helper per person (arms the opening). |
| `garagedoor`, `doorbell` | `camera` | `camera.*`. |
| `doorbell` | `doorbell` | `binary_sensor` or `event.*` for the doorbell button. |
| `doorbell` | `chime` | `number.*` or `input_number.*`; `media_player` for TV streams. |
| `end_vacation` | `vacation_switch`, `presence`, `vacation_ends` | `input_boolean` (vacation) and `input_datetime` helpers with date and time; `person.*`. |
| `wake_up` | `time`, `alarm_switch`, `alarm_switch_non_work_day` | `input_datetime` helper with **time only**; two `input_boolean` helpers. |
| `wake_up` | `media_player`, `wake_up_lights` | `media_player.*`; `light.*` (or zigbee2mqtt topics for `wake_up_MQTTlights`). |
| `appliance_notify` | `dryer_power`, `dryer_switch` | `sensor` with `device_class` `power` and unit `W` for the appliance; optionally its `switch.*` (smart plug). |
| `appliance_home_connect` | `remote_start`, `active_program` | Search `"integration":"home_connect"`: a `binary_sensor` for remote start and a `select` for the active program. Program names are the values in the select's `options`. |
| `espresso_machine` | `espresso_machine`, `coffee_timer` | `switch.*` (smart plug); `input_datetime` helper. |
| `log_energy_usage` | `items[].entity` | `sensor` with `device_class` `energy`, unit `kWh`, `state_class` `total_increasing` or `total` (cumulative meters only). |
| `charger_controller` | `charger_switch`, `battery_level`, `battery_state`, `device_location` | `switch.*` for the plug; Companion app sensors (`"integration":"mobile_app"`): `device_class` `battery` and a battery state sensor; `device_tracker.*`. |
| `media_pause`, `media_stop` | `sensors`, `media_player` | `binary_sensor` with `device_class` `occupancy`, `motion` or `presence`; `media_player.*`. |
| `fire_alarm` | `alarms`, `turn_off`, `screens` | `binary_sensor` with `device_class` `smoke`; `switch.*` to cut; `cover.*` to open. |
| `change_dns_cloudflare` | `ip_sensor` | Optional `sensor` with your public IP. Cloudflare ids and token go in `secrets.yaml`. |

## Writing the YAML

- `apps.yaml` lives in the AppDaemon `apps` folder, **next to** the folder this repository is cloned into, not inside it. With the Home Assistant AppDaemon add-on it is in the add-on's config folder under `apps/`.
- Every app block has a name, `module` and `class`, plus its keys. Copy the example from the app's README section and replace the values.
- YAML is strict about spaces. Use two spaces for each level, never tabs.
- Keep secrets (Cloudflare token and ids) in AppDaemon's `secrets.yaml` and refer to them with `!secret name`.
- AppDaemon reloads an app when `apps.yaml` or the app's `.py` file changes, no restart needed.
- Do not put other `.yaml` or `.yml` files in this folder. AppDaemon reads every YAML file under `apps/` as app configuration.

## Tips

- Set `log_level: DEBUG` in an app's block while testing, and remove it later.
- A sensor that shows `unavailable` or `unknown` is a Home Assistant problem, not an app problem. Fix the device or battery first.
- Start with one app, check it works, then add the next. Add `notify_mobiles` before everything else.
- Test door and safety apps while you are home, with the device in front of you.
- If an app seems to do nothing: check the log for ERROR lines, check the entity ids with `grep` in the index, and check that `notify_receiver` matches a `person:` label in `notify_mobiles`.
- Run `tools/ha_snapshot.py` again after you add devices or rename entities. The index is a snapshot.

## Keeping your data out of git

- Everything personal lives in `.local/`, which `.gitignore` excludes: the token, the address and the index. The script stops with a message if git does not ignore it.
- If you copied this repository without its `.gitignore`, add the line `.local/` to it before running the script.
- Before you ever commit or push your own changes, run `git status` and make sure nothing from `.local/` and no `apps.yaml` with private details is listed.

## When you are done

Delete the token in Home Assistant: profile, **Security**, **Long-lived access tokens**, delete `AI assistant`. Then delete `.local/ha_token`. Create a new token the next time you want to refresh the index.
