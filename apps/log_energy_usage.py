""" Logging of consumption

    Logs the cost of cumulative kWh sensors for every price period, per day and per month.

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.2.0"

from appdaemon import adbase as ad
import datetime
import calendar
import csv
import json
import os
import shutil

DEFAULT_MAX_KW = 100.0
DELIMITER = '\t'


def guest_column(item:dict) -> str | None:
    """ Name of the column for guest usage, or None if the item has no guestUse """

    if 'guestUse' not in item:
        return None
    return item.get('guest_name', f"{item['name']}Guest")


class MeterGuard:
    """ Turns readings from a cumulative kWh sensor into consumption.

        - A normal change is accepted. It can be negative, for example net metering with solar.
        - A change larger than max_kw could deliver in the elapsed time is not trusted at once.
          If the next reading is back close to the old value it was a glitch and is dropped.
          If the next reading stays at the new level, the sensor really changed:
          a reset to zero counts the new value as consumption, anything else (a replaced meter)
          counts as no consumption and the new value becomes the new baseline.
    """

    def __init__(self, name:str, baseline:float, time:datetime.datetime, max_kw:float):
        self.name = name
        self.baseline = baseline
        self.time = time
        self.max_kw = max_kw
        self.pending = None

    def update(self, value:float, now:datetime.datetime) -> tuple[float | None, str | None]:
        """ Returns (consumption in kWh or None if the reading is not used yet, event) """

        limit = self.max_kw * max((now - self.time).total_seconds() / 3600, 1 / 60)
        delta = value - self.baseline
        if abs(delta) <= limit:
            self.baseline = value
            self.time = now
            self.pending = None
            return delta, None

        if self.pending is not None:
            pending_value, pending_time = self.pending
            pending_limit = self.max_kw * max((now - pending_time).total_seconds() / 3600, 1 / 60)
            if abs(value - pending_value) <= pending_limit:
                old_baseline = self.baseline
                self.baseline = value
                self.time = now
                self.pending = None
                if 0 <= value < old_baseline and value <= limit:
                    return value, 'reset'
                return 0.0, 'step'

        self.pending = (value, now)
        return None, 'ignored'


class LogEnergyUsage(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        name_of_priceCalc_app = self.args.get('electricalPriceApp', 'electricalPriceCalc')
        self.electricalPrice = self.ADapi.get_app(name_of_priceCalc_app)
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        if self.electricalPrice is None or self.notify_app is None:
            self.ADapi.log(
                f"{self.name}: Could not find app '{name_of_priceCalc_app}' or '{name_of_notify_app}'. "
                "Add them to 'dependencies'. Aborting setup",
                level = 'ERROR'
            )
            return
        self.notify_receiver = self.args['notify_receiver']

        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.csv_folder = self.args.get('csv_folder_path', '/conf/db/')
        self.max_kw = float(self.args.get('max_kw', DEFAULT_MAX_KW))
        try:
            os.makedirs(self.csv_folder, exist_ok = True)
        except OSError as e:
            self.ADapi.log(f"Not able to create {self.csv_folder}: {e}", level = 'ERROR')

        self.items:list = self.args['items']
        # Columns in the files: every item, followed by its guest column if it has guestUse
        self.columns:list = []
        for item in self.items:
            self.columns.append(item['name'])
            guest_col = guest_column(item)
            if guest_col is not None:
                self.columns.append(guest_col)
        self.usage_data_total:dict = {}
        self.usage_data_daily_cost:dict = {}
        self.guest_usage:dict = {}
        self.guards:dict = {}
        saved_time = self.ADapi.get_now()

        try:
            with open(self._path('daily_tmp_storage.json'), 'r') as json_read:
                ConsumptionData = json.load(json_read)
            self.usage_data_total = ConsumptionData.get('Consumption', {})
            self.usage_data_daily_cost = ConsumptionData.get('Cost', {})
            self.guest_usage = ConsumptionData.get('Guest', {})
            if 'Updated' in ConsumptionData:
                saved_time = datetime.datetime.fromisoformat(ConsumptionData['Updated'])
            else:
                # State saved by an older version. The file time tells when it was saved.
                saved_time = datetime.datetime.fromtimestamp(os.path.getmtime(self._path('daily_tmp_storage.json')), tz = saved_time.tzinfo)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, AttributeError, TypeError) as e:
            self.ADapi.log(f"Not able to read saved state from {self._path('daily_tmp_storage.json')}: {e}", level = 'WARNING')

        unavailable:list = []
        for item in self.items:
            name = item['name']
            item_max_kw = float(item.get('max_kw', self.max_kw))
            if name in self.usage_data_total:
                self.guards[name] = MeterGuard(name, float(self.usage_data_total[name]), saved_time, item_max_kw)
            else:
                usage = self._read_item(item)
                if usage is None:
                    unavailable.append(name)
                else:
                    self.usage_data_total[name] = usage
                    self.guards[name] = MeterGuard(name, usage, self.ADapi.get_now(), item_max_kw)
        for column in self.columns:
            if column not in self.usage_data_daily_cost:
                self.usage_data_daily_cost[column] = 0
        for item in self.items:
            guest_col = guest_column(item)
            if guest_col is not None and guest_col not in self.usage_data_total:
                self.usage_data_total[guest_col] = 0.0

        if unavailable:
            names = ', '.join(unavailable)
            self.ADapi.log(
                f"Consumption for {names} not available when creating usage logging. "
                "Logging starts when it is available.",
                level = 'WARNING'
            )
            self.notify_app.send_notification(
                message = f"Consumption for {names} not available when creating usage logging. Logging starts when it is available.",
                message_title = "Log Energy Usage",
                message_recipient = self.notify_receiver,
                also_if_not_home = True
            )

        self.ADapi.run_in(self._create_runtimes, 10)

    def terminate(self) -> None:
        """ Writes consumption data to persistent storage before terminating app """

        if getattr(self, 'guards', None) is not None:
            self._save_state()

    def _path(self, filename:str) -> str:
        return os.path.join(self.csv_folder, filename)

    def _read_item(self, item:dict) -> float | None:
        """ Returns the cumulative reading or None if it is not available """

        namespace = item.get('namespace', self.HASS_namespace)
        try:
            return float(self.ADapi.get_state(item['entity'], namespace = namespace))
        except (TypeError, ValueError):
            return None

    def _save_state(self) -> None:
        ConsumptionData:dict = {
            'Consumption' : self.usage_data_total,
            'Cost' : self.usage_data_daily_cost,
            'Guest' : self.guest_usage,
            'Updated' : self.ADapi.get_now().isoformat(),
        }
        path = self._path('daily_tmp_storage.json')
        try:
            with open(path + '.tmp', 'w') as json_write:
                json.dump(ConsumptionData, json_write, indent = 4)
            os.replace(path + '.tmp', path)
        except (OSError, TypeError, ValueError) as e:
            self.ADapi.log(f"Error occurred while writing {path}: {e}", level = 'WARNING')

    def _create_runtimes(self, **kwargs):
        lastStartTime = None
        now = self.ADapi.get_now()
        for item in getattr(self.electricalPrice, 'elpricestoday', None) or []:
            lastStartTime = item.end
            if lastStartTime >= now:
                self.ADapi.run_at(self._daily_usage, lastStartTime, price = item.value)
                if now.day != lastStartTime.day:
                    break
        if lastStartTime is None or lastStartTime < now:
            # The price app has no prices right now. Try again later.
            self.ADapi.log("No electricity prices available yet for usage logging. Trying again in 10 minutes.", level = 'INFO')
            self.ADapi.run_in(self._create_runtimes, 600)
            return
        self.ADapi.run_at(self._register_daily_cost, lastStartTime + datetime.timedelta(seconds = 2))
        self.ADapi.run_at(self._create_runtimes, lastStartTime + datetime.timedelta(minutes = 3))
        if now.day == calendar.monthrange(now.year, now.month)[1]:
            self.ADapi.run_at(self._calculate_monthly_consumption, lastStartTime + datetime.timedelta(minutes = 1))

    def _daily_usage(self, **kwargs):
        price_now = kwargs['price']
        now = self.ADapi.get_now()

            # Usage consumption total every price period:
        for item in self.items:
            name = item['name']
            usage = self._read_item(item)
            if usage is None:
                self.ADapi.log(f"Consumption for {name} not available when logging usage", level = 'INFO')
                continue

            guard = self.guards.get(name)
            if guard is None:
                # Was not available at startup. The first reading is the baseline.
                guard = MeterGuard(name, usage, now, float(item.get('max_kw', self.max_kw)))
                self.guards[name] = guard
                self.usage_data_total[name] = usage
                continue

            consumption, event = guard.update(usage, now)
            if event == 'ignored':
                self.ADapi.log(f"{name}: reading {usage} is {round(usage - guard.baseline, 1)} kWh from last value. Waiting for the next reading before using it.", level = 'INFO')
            elif event is not None:
                self.ADapi.log(f"{name}: sensor changed from {round(self.usage_data_total[name], 2)} to {usage} ({event}). Using it as the new starting point.", level = 'WARNING')
            if consumption is None:
                continue

            # Usage cost every price period:
            item_price = float(consumption * price_now)
            self.usage_data_total[name] = guard.baseline
            guest_slot = False
            guest_col = guest_column(item)
            if guest_col is not None:
                guestUsage:float = 0
                namespaceGuest = item.get('namespace_guest', self.HASS_namespace)
                if self.ADapi.get_state(item['guestUse'], namespace = namespaceGuest) == 'on':
                    guest_slot = True
                    guestUsage += float(self.guest_usage.get(name, 0))
                    guestUsage += item_price
                    self.guest_usage[name] = guestUsage
                elif float(self.guest_usage.get(name, 0)) > 0:
                    # The last period of the guest. Notifies the total cost.
                    guest_slot = True
                    guestUsage += float(self.guest_usage[name])
                    guestUsage += item_price
                    self.ADapi.log(f"Guest Consumption cost for {name} was {round(guestUsage,2)}", level = 'INFO')
                    self.notify_app.send_notification(
                        message = f"Guest Consumption cost for {name} was {round(guestUsage,2)}",
                        message_title = "Guest Energy Usage",
                        message_recipient = self.notify_receiver,
                        also_if_not_home = True
                    )
                    self.guest_usage[name] = 0
            if guest_slot:
                # Guest usage is logged in its own column and is not part of the item's own column.
                self.usage_data_daily_cost[guest_col] = float(self.usage_data_daily_cost.get(guest_col, 0)) + item_price
                self.usage_data_total[guest_col] = float(self.usage_data_total.get(guest_col, 0)) + consumption
            else:
                self.usage_data_daily_cost[name] = float(self.usage_data_daily_cost.get(name, 0)) + item_price

        self._save_state()

    # ------------------------------------------------------------------
    #  Files
    # ------------------------------------------------------------------
    def _ensure_header(self, path:str, fieldnames:list) -> None:
        """ If the file has another header than fieldnames (items were changed), the file is
            rewritten with the new header. Values are kept by column name, new columns are empty
            and columns of removed items are dropped. The old file is saved as .bak """

        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            return
        with open(path, 'r', newline = '') as csv_file:
            header = next(csv.reader(csv_file, delimiter = DELIMITER), None)
        if header == fieldnames:
            return
        backup = path + '.bak'
        if os.path.exists(backup):
            backup = f"{path}.{self.ADapi.get_now().strftime('%Y%m%d%H%M%S')}.bak"
        shutil.copy2(path, backup)
        with open(path, 'r', newline = '') as csv_file:
            rows = list(csv.DictReader(csv_file, delimiter = DELIMITER))
        with open(path, 'w', newline = '') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames = fieldnames, delimiter = DELIMITER, restval = '', extrasaction = 'ignore')
            writer.writeheader()
            writer.writerows(rows)
        self.ADapi.log(
            f"The items changed, so the header of {path} was updated. The old file is saved as {backup}",
            level = 'WARNING'
        )

    def _append_row(self, filename:str, fieldnames:list, row:dict) -> None:
        path = self._path(filename)
        self._ensure_header(path, fieldnames)
        is_new = not os.path.isfile(path) or os.path.getsize(path) == 0
        with open(path, 'a', newline = '') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames = fieldnames, delimiter = DELIMITER, restval = '', extrasaction = 'ignore')
            if is_new:
                writer.writeheader()
            writer.writerow(row)

    def _read_rows(self, filename:str, fieldnames:list) -> list:
        path = self._path(filename)
        self._ensure_header(path, fieldnames)
        if not os.path.isfile(path):
            return []
        with open(path, 'r', newline = '') as csv_file:
            return list(csv.DictReader(csv_file, delimiter = DELIMITER))

    def _register_daily_cost(self, **kwargs):
        self._append_row('every_day_cost_usage.csv', self.columns, self.usage_data_daily_cost)
        for column in self.columns:
            self.usage_data_daily_cost[column] = 0
        self._save_state()

    def _calculate_monthly_consumption(self, **kwargs):
        # Register monthly consumption
        last_month_date = get_last_month(self.ADapi.get_now())
        date_str = last_month_date.strftime("%Y:%m")
        columns = self.columns
        fieldnames = ['Date'] + columns

        usage_data_total:dict = {'Date' : date_str}
        usage_data_total_monthly:dict = {'Date' : date_str}
        for column in columns:
            if column in self.usage_data_total:
                usage_data_total[column] = round(float(self.usage_data_total[column]), 2)

        last_rows = self._read_rows('total_energy_usage.csv', fieldnames)
        last_month_data:dict = last_rows[-1] if last_rows else usage_data_total
        self._append_row('total_energy_usage.csv', fieldnames, usage_data_total)

        # Consumption last month. A guest column is a counter that started at 0.
        raw_consumption:dict = {}
        for item in self.items:
            name = item['name']
            try:
                raw_consumption[name] = float(usage_data_total[name]) - float(last_month_data[name])
            except (TypeError, ValueError, KeyError):
                raw_consumption[name] = 0
            guest_col = guest_column(item)
            if guest_col is not None:
                try:
                    previous = float(last_month_data.get(guest_col) or 0)
                    raw_consumption[guest_col] = float(usage_data_total.get(guest_col, 0)) - previous
                except (TypeError, ValueError):
                    raw_consumption[guest_col] = 0
                # The guest part is not part of the item's own consumption
                raw_consumption[name] -= raw_consumption[guest_col]
        consumption_this_month:float = raw_consumption.get('Total', 0)
        for column in columns:
            usage_data_total_monthly[column] = round(raw_consumption[column], 2)
        self._append_row('monthly_energy_usage.csv', fieldnames, usage_data_total_monthly)

        monthcost:dict = {column: 0.0 for column in columns}
        for line in self._read_rows('every_day_cost_usage.csv', columns):
            for column in columns:
                try:
                    monthcost[column] += float(line[column])
                except (ValueError, TypeError, KeyError) as e:
                    self.ADapi.log(f"Error extracting {column} from: \n{line}\n{e}", level = 'WARNING')

        usage_data_monthly_cost:dict = {'Date' : date_str, 'Price' : 0}
        inputTexts:dict = {}
        for column in columns:
            usage_data_monthly_cost[column] = round(monthcost[column], 2)
        for item in self.items:
            name = item['name']
            if 'input_text' in item:
                inputTexts[item['input_text']] = inputTexts.get(item['input_text'], 0) + monthcost[name]
            if name == 'Total':
                usage_data_monthly_cost['Price'] = round(monthcost[name] / consumption_this_month, 3) if consumption_this_month else 0
        self._append_row('monthly_cost_usage.csv', ['Date', 'Price'] + columns, usage_data_monthly_cost)

        # Write info to input texts
        currency = getattr(self.electricalPrice, 'currency', '')
        month_name = last_month_date.strftime('%B')
        for item in self.items:
            if 'input_text' in item:
                inputtextname = item['input_text']
                namespace = item.get('namespace_input_text', self.HASS_namespace)
                totalprice = inputTexts[inputtextname]
                self.ADapi.log(
                    f"{item['name']} consumption in {month_name} is {round(float(totalprice),2)} {currency}"
                )
                self.ADapi.call_service('input_text/set_value',
                    value = f'{month_name} {round(float(totalprice),2)} {currency}',
                    entity_id = inputtextname,
                    namespace = namespace
                )

        self.ADapi.run_in(self._empty_daily_file, 10)

    def _empty_daily_file(self, **kwargs):
        with open(self._path('every_day_cost_usage.csv'), 'w', newline = '') as csv_hourly_write:
            csv_writer_hourly = csv.DictWriter(csv_hourly_write, fieldnames = self.columns, delimiter = DELIMITER)
            csv_writer_hourly.writeheader()

    def only_write_consumption_to_input_text(self, id):
        """ Use this to write the cost so far this month to the input_text of the item with name equal to id,
            for example from a terminal or a temporary call at the end of initialize. """

        inputtextname:str = ''
        namespace:str = ''
        for item in self.items:
            if item['name'] == id:
                if 'input_text' in item:
                    inputtextname = item['input_text']
                    namespace = item.get('namespace_input_text', self.HASS_namespace)
                else:
                    return

        totalprice:float = 0.0
        for line in self._read_rows('every_day_cost_usage.csv', self.columns):
            try:
                totalprice += float(line[id])
            except (ValueError, TypeError, KeyError) as e:
                self.ADapi.log(f"Error extracting {id} from: \n{line}\n{e}", level = 'WARNING')

        # Write info to input texts
        currency = getattr(self.electricalPrice, 'currency', '')
        self.ADapi.log(f'Consumption at {id} is : {round(float(totalprice),2)} {currency}')

        self.ADapi.call_service('input_text/set_value',
            value = f'{self.ADapi.get_now().date()} : {round(float(totalprice),2)} {currency}',
            entity_id = inputtextname,
            namespace = namespace
        )

def get_last_month(now:datetime.datetime) -> datetime.date:
    """ First day of the month before the month of now """

    if now.month == 1:
        return datetime.date(now.year - 1, 12, 1)
    return datetime.date(now.year, now.month - 1, 1)
