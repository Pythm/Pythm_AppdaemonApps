""" Logging of consumption

    @Pythm / https://github.com/Pythm
"""
__version__ = "0.1.0"

from appdaemon import adbase as ad
import datetime
import calendar
import csv
import json
import os


class LogEnergyUsage(ad.ADBase):

    def initialize(self):
        self.ADapi = self.get_ad_api()
        name_of_priceCalc_app = self.args.get('electricalPriceApp', 'electricalPriceCalc')
        self.electricalPrice = self.ADapi.get_app(name_of_priceCalc_app)
        name_of_notify_app = self.args.get('notify_app', 'notify_mobiles')
        self.notify_app = self.ADapi.get_app(name_of_notify_app)
        self.notify_reciever = self.args['notify_reciever']

        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.csv_folder = self.args.get('csv_folder_path', '/conf/db/')

        self.items:list = self.args['items']
        self.usage_data_total:dict = {}
        self.usage_data_daily_cost:dict = {}

        try:
            with open(self.csv_folder + 'daily_tmp_storage.json', 'r') as json_read:
                ConsumptionData = json.load(json_read)
                if 'Consumption' in ConsumptionData:
                    self.usage_data_total = ConsumptionData['Consumption']
                if 'Cost' in ConsumptionData:
                    self.usage_data_daily_cost = ConsumptionData['Cost']

        except FileNotFoundError:
            self.ADapi.run_in(self._daily_usage, 2, price = 0)

        for item in self.items:
            name = item['name']
            if not name in self.usage_data_total:
                try:
                    usage = float(self.ADapi.get_state(item['entity']))
                    item.update({'usage': usage})
                except Exception as e:
                    self.ADapi.log(
                        f"Consumption for {name} not available when creating usage logging. "
                        f"Please restart app when it is available: {e}",
                        level = 'WARNING'
                        )
                    self.notify_app.send_notification(
                        message = f"Consumption for {name} not available when creating usage logging. Please restart app when it is available",
                        message_title = "Log Energy Usage",
                        message_recipient = self.notify_reciever,
                        also_if_not_home = True
                    )
                else:
                    self.usage_data_total.update({name : usage})
            else:
                item.update({'usage': self.usage_data_total[name]})
            if not name in self.usage_data_daily_cost:
                self.usage_data_daily_cost.update({name : 0})

        self.ADapi.run_in(self._create_runtimes, 10)

        """ Use this to print out to input text with name to get price before end of month
            with id equal to Name containing the input_text
        """
        #self.only_write_consumption_to_input_text(id = 'Leil')

    def terminate(self) -> None:
        """ Writes consumption data to persisten storage before terminating app.
        """
        ConsumptionData:dict = {}
        ConsumptionData.update({'Consumption' : self.usage_data_total})
        ConsumptionData.update({'Cost' : self.usage_data_daily_cost})
        try:
            with open(self.csv_folder + 'daily_tmp_storage.json', 'w') as json_write:
                try:
                    json.dump(ConsumptionData, json_write, indent = 4)
                except Exception as e:
                    self.ADapi.log(f"Error occurred while writing to JSON on Terminate: {e}")

        except FileNotFoundError:
            self.ADapi.log(f"FileNotFound when Log Energy Usage Terminated", level = 'INFO')

    def _create_runtimes(self, kwargs):
        lastStartTime = None
        for item in self.electricalPrice.elpricestoday:
            lastStartTime = item['end']
            if lastStartTime >= self.ADapi.datetime(aware=True):
                self.ADapi.run_at(self._daily_usage, lastStartTime, price = item['value'])
                if self.ADapi.datetime(aware=True).day != lastStartTime.day:
                    break
        self.ADapi.run_at(self._register_daily_cost, lastStartTime + datetime.timedelta(seconds = 2))
        self.ADapi.run_at(self._create_runtimes, lastStartTime + datetime.timedelta(minutes = 3))
        if self.ADapi.datetime().day == calendar.monthrange(self.ADapi.datetime().year, self.ADapi.datetime().month)[1]:
            self.ADapi.run_at(self._calulate_montly_consumption, lastStartTime + datetime.timedelta(minutes = 1))

    def _daily_usage(self, kwargs):
        price_now = kwargs['price']

            # Usage consumption total every Hour:
        for item in self.items:
            name = item['name']
            try:
                usage = float(self.ADapi.get_state(item['entity']))
                item.update({'usage': usage})
            except Exception as e:
                self.ADapi.log(f"Consumption for {name} not available when logging usage: {e}", level = 'INFO')
                self.notify_app.send_notification(
                    message = f"Consumption for {name} not available when logging usage",
                    message_title = "Log Energy Usage",
                    message_recipient = self.notify_reciever,
                    also_if_not_home = True
                )
            else:
                # Usage cost every Hour:
                item_price = float((item['usage'] - float(self.usage_data_total[name])) * price_now)
                if 'guestUse' in item:
                    guestUsage:float = 0
                    namespaceGuest = item.get('namespace_guest', self.HASS_namespace)
                    if self.ADapi.get_state(item['guestUse'], namespace = namespaceGuest) == 'on':
                        if 'guestUsage' in item:
                            guestUsage += float(item['guestUsage'])
                        guestUsage += item_price
                        item.update({'guestUsage': guestUsage})
                    else:
                        if 'guestUsage' in item:
                            if float(item['guestUsage']) > 0:
                                self.ADapi.log(f"Guest Consumption for {name} was {item['guestUsage']}", level = 'INFO')
                                self.notify_app.send_notification(
                                    message = f"Guest Consumption for {name} was {item['guestUsage']}",
                                    message_title = "Guest Energy Usage",
                                    message_recipient = self.notify_reciever,
                                    also_if_not_home = True
                                )
                                item.update({'guestUsage': 0})
                item_price += float(self.usage_data_daily_cost[name])
                self.usage_data_daily_cost.update({name : item_price})
                self.usage_data_total.update({name : usage})

    def _register_daily_cost(self, kwargs):
        fieldnames = [item['name'] for item in self.items]
        try:
            with open(str(self.csv_folder) + 'every_day_cost_usage.csv', 'r+') as csv_hourly:
                csv_reader_hourly = csv.DictReader(csv_hourly, fieldnames=fieldnames, delimiter='\t')
                csv_writer_hourly = csv.DictWriter(csv_hourly, fieldnames=fieldnames, delimiter='\t')
                next(csv_reader_hourly)
                for line in csv_reader_hourly:
                    pass

                csv_writer_hourly.writerow(self.usage_data_daily_cost)

        except FileNotFoundError:
            with open(str(self.csv_folder) + 'every_day_cost_usage.csv', 'w') as csv_hourly_write:
                csv_writer_hourly = csv.DictWriter(csv_hourly_write, fieldnames=fieldnames, delimiter='\t')
                csv_writer_hourly.writeheader()
                csv_writer_hourly.writerow(self.usage_data_daily_cost)
        else:
            for item in self.items:
                name = item['name']
                self.usage_data_daily_cost.update({name : 0})

    def _calulate_montly_consumption(self, kwargs):
        # Register montly consumption
        usage_data_total:dict = {}
        usage_data_total_montly:dict = {}
        last_month_date = get_last_month()
        usage_data_total.update({'Date' : last_month_date.strftime("%Y:%m")})
        usage_data_total_montly.update({'Date' : last_month_date.strftime("%Y:%m")})
        last_month_data:dict = {}
        consumption_this_month:float = 0

        for item in self.items:
            name = item['name']
            item_consumption = item['usage']
            usage_data_total.update({name : round(item_consumption,2)})

        fieldnames = ['Date']
        fieldnames += [item['name'] for item in self.items]
        try:
            with open(str(self.csv_folder) + 'total_energy_usage.csv', 'r+') as csv_total:
                csv_reader_total = csv.DictReader(csv_total, fieldnames=fieldnames, delimiter='\t')
                csv_writer_total = csv.DictWriter(csv_total, fieldnames=fieldnames, delimiter='\t')

                next(csv_reader_total)
                for line in csv_reader_total:
                    last_month_data = line

                csv_writer_total.writerow(usage_data_total)

        except FileNotFoundError:
            with open(str(self.csv_folder) + 'total_energy_usage.csv', 'w') as csv_total:
                csv_writer_total = csv.DictWriter(csv_total, fieldnames=fieldnames, delimiter='\t')
                csv_writer_total.writeheader()

                csv_writer_total.writerow(usage_data_total)
                last_month_data = usage_data_total

        for item in self.items:
            name = item['name']
            item_consumption = item['usage'] - float(last_month_data[name])
            usage_data_total_montly.update({name : round(item_consumption,2)})
            if name == 'Total':
                consumption_this_month = item_consumption
        try:
            with open(str(self.csv_folder) + 'monthly_energy_usage.csv', 'r+') as csv_monthly:
                csv_writer_monthly = csv.DictWriter(csv_monthly, fieldnames=fieldnames, delimiter='\t')
                csv_monthly.seek(0, os.SEEK_END)

                csv_writer_monthly.writerow(usage_data_total_montly)

        except FileNotFoundError:
            with open(str(self.csv_folder) + 'monthly_energy_usage.csv', 'w') as csv_monthly:
                csv_writer_monthly = csv.DictWriter(csv_monthly, fieldnames=fieldnames, delimiter='\t')
                csv_writer_monthly.writeheader()

        # Skriv Kostnad
        usage_data_monthy_cost:dict = {}
        usage_data_monthy_cost.update({'Date' : last_month_date.strftime("%Y:%m")})
        usage_data_monthy_cost.update({'Price' : 0})
        for item in self.items:
            item.update({'monthcost': 0.0})

        inputTexts:dict = {}
        for item in self.items:
            if 'input_text' in item:
                inputTexts.update({item['input_text']: 0})

        fieldnames = [item['name'] for item in self.items]
        with open(str(self.csv_folder) + 'every_day_cost_usage.csv', 'r') as csv_hourly:
            csv_reader_hourly = csv.DictReader(csv_hourly, fieldnames=fieldnames, delimiter='\t')

            next(csv_reader_hourly)
            for line in csv_reader_hourly:
                for item in self.items:
                    name = item['name']
                    try:
                        item['monthcost'] += float(line[name])
                    except (ValueError, TypeError) as e:
                        self.ADapi.log(f"Error extracting {name} from: \n{line}\n{e}", level = 'WARNING')

            for item in self.items:
                name = item['name']
                usage_data_monthy_cost.update({item['name'] : round(item['monthcost'],2)})
                if 'input_text' in item:
                    inputtextname = item['input_text']
                    totalprice = inputTexts[inputtextname] + item['monthcost']
                    inputTexts.update({inputtextname: totalprice})
                if name == 'Total':
                    consumption_this_month = round(item['monthcost'] / consumption_this_month,3)
                    usage_data_monthy_cost.update({'Price' : consumption_this_month})

        fieldnames = ['Date', 'Price']
        fieldnames += [item['name'] for item in self.items]
        try:
            with open(str(self.csv_folder) + 'monthly_cost_usage.csv', 'r+') as csv_cost:
                csv_writer_cost = csv.DictWriter(csv_cost, fieldnames=fieldnames, delimiter='\t')
                csv_cost.seek(0, os.SEEK_END)
                csv_writer_cost.writerow(usage_data_monthy_cost)

        except FileNotFoundError:
            with open(str(self.csv_folder) + 'monthly_cost_usage.csv', 'w') as csv_cost:
                csv_writer_cost = csv.DictWriter(csv_cost, fieldnames=fieldnames, delimiter='\t')
                csv_writer_cost.writeheader()

                csv_writer_cost.writerow(usage_data_monthy_cost)

        # Write info to input texts
        mndnavn = datetime.datetime.now() - datetime.timedelta(days = 1)
        for item in self.items:
            if 'input_text' in item:
                inputtextname = item['input_text']
                namespace = item.get('namespace_input_text', self.HASS_namespace)
                totalprice = inputTexts[inputtextname]
                self.ADapi.log(
                    f"{item['name']} consumption in {mndnavn.strftime('%B')} is {round(float(totalprice),2)} {self.electricalPrice.currency}"
                )
                self.ADapi.call_service('input_text/set_value',
                    value = f'{mndnavn.strftime("%B")} {round(float(totalprice),2)} {self.electricalPrice.currency}',
                    entity_id = inputtextname,
                    namespace = namespace
                )

        self.ADapi.run_in(self._empty_daily_file, 10)

    def _empty_daily_file(self, kwargs):
        fieldnames = [item['name'] for item in self.items]

        with open(str(self.csv_folder) + 'every_day_cost_usage.csv', 'w') as csv_hourly_write:
            csv_writer_hourly = csv.DictWriter(csv_hourly_write, fieldnames=fieldnames, delimiter='\t')
            csv_writer_hourly.writeheader()

    def only_write_consumption_to_input_text(self, id):
        inputtextname:str = ''
        namespace:str = ''
        for item in self.items:
            if item['name'] == id:
                if 'input_text' in item:
                    item.update({'monthcost': 0.0})
                    inputtextname = item['input_text']
                    namespace = item.get('namespace_input_text', self.HASS_namespace)
                else:
                    return

        totalprice:float = 0.0
        fieldnames = [item['name'] for item in self.items]
        with open(str(self.csv_folder) + 'every_day_cost_usage.csv', 'r') as csv_hourly:
            csv_reader_hourly = csv.DictReader(csv_hourly, fieldnames=fieldnames, delimiter='\t')

            next(csv_reader_hourly)
            for line in csv_reader_hourly:
                for item in self.items:
                    if item['name'] == id:
                        try:
                            totalprice += float(line[id])
                        except (ValueError, TypeError) as e:
                            self.ADapi.log(f"Error extracting {id} from: \n{line}\n{e}", level = 'WARNING')

        # Write info to input texts
        self.ADapi.log(f'Consumption at {id} is : '
                        f'{round(float(totalprice),2)} {self.electricalPrice.currency}')

        self.ADapi.call_service('input_text/set_value',
            value = f'{datetime.date.today()} : {round(float(totalprice),2)} {self.electricalPrice.currency}',
            entity_id = inputtextname,
            namespace = namespace
        )

def get_last_month():
    d = datetime.date.today()
    year = d.year
    month = d.month

    if month == 1:
        return datetime.date(year - 1, 12, 1)
    else:
        return datetime.date(year, month - 1, 1)
