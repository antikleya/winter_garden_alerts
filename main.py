from firebase_admin import db, initialize_app, credentials
from datetime import datetime
from typing import Dict
from config import db_config, bot_config
from threading import Timer
import asyncio
import telegram
import logging
import os
import pytz


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class Alert:
    def __init__(self, log_str: str, bot: telegram.Bot):
        self.log_tag = log_str
        self.alert_flag = False
        self.bot = bot





class AlertHandler:
    def __init__(self, token: str, channel: str, db_reference, time_interval: int = 40, timer_delay: float = 5,
                 tz = pytz.timezone('Europe/Moscow')):
        self.bot = telegram.Bot(token)
        self.db_reference = db_reference
        self.channel = channel
        self.alert_flag = False
        self.reboot_flag = False
        self.time_interval = time_interval
        self.timer_delay = int(timer_delay * 60)
        self.tz = tz
        self.datapoint = {}

    def get_log_message(self, difference: int, time: datetime, send_alert: bool, reboot_alert: bool) -> str:
        return f"[{datetime.now(tz=self.tz).strftime('%H:%M %d/%m/%Y')}] " \
               f"{'NO_DATA_ALERT ' if self.alert_flag else ''}" \
               f"{'REBOOT_ALERT ' if self.reboot_flag else ''}" \
               f"Last datapoint timestamp - {time.strftime('%H:%M %d/%m/%Y')}. " \
               f"Current difference is {difference}. {'NO DATA ALERT SENT. ' if send_alert else ''}" \
               f"{'REBOOT ALERT SENT.' if reboot_alert else ''}"

    def get_last_datapoint_date(self) -> datetime:
        snapshot = self.db_reference.order_by_child('timestamp').limit_to_last(1).get()
        date = datetime.fromtimestamp(list(snapshot.values())[0]['timestamp'] - 10800, tz=self.tz)
        self.datapoint = list(snapshot.values())[0]
        return date

    async def alert(self, difference: int):
        async with self.bot:
            await self.bot.send_message(self.channel, f"[ALERT] No data sent for {difference} minutes")

    async def reboot_alert(self):
        async with self.bot:
            await self.bot.send_message(self.channel, f"[ALERT] Reboot detected")

    def no_data_alert_handler(self, last_timestamp: datetime) -> Dict:
        now = datetime.now(tz=self.tz)
        difference = now - last_timestamp
        diff_in_minutes = difference.seconds // 60
        send_alert = False

        if (diff_in_minutes > self.time_interval) and (not self.alert_flag):
            asyncio.run(self.alert(difference=diff_in_minutes))
            send_alert = True
            self.alert_flag = True
        elif diff_in_minutes < self.time_interval:
            self.alert_flag = False

        return {'diff_in_minutes': diff_in_minutes, 'send_alert': send_alert}

    def reboot_alert_handler(self) -> bool:
        reboot_alert = False

        if self.datapoint['reboot'] & (not self.reboot_flag):
            asyncio.run(self.reboot_alert())
            reboot_alert = True
            self.reboot_flag = True
        elif not self.datapoint['reboot']:
            self.reboot_flag = False

        return reboot_alert

    def monitor(self):
        last_datapoint_time = self.get_last_datapoint_date()

        no_data_result = self.no_data_alert_handler(last_datapoint_time)
        reboot_alert = self.reboot_alert_handler()
        self.clear_garbage_datapoints()

        logging.info(self.get_log_message(
            no_data_result['diff_in_minutes'],
            last_datapoint_time,
            no_data_result['send_alert'],
            reboot_alert)
        )

    def start(self):
        timer = RepeatTimer(self.timer_delay, self.monitor)
        timer.start()
        x = ''
        try:
            while 1:
                pass
        except:
            timer.cancel()

    def clear_garbage_datapoints(self):
        print(self.datapoint['timestamp'])
        if self.datapoint['timestamp'] > datetime.now(tz=self.tz).timestamp() + 3600:
            self.db_reference.child(list(self.db_reference.order_by_child('timestamp').limit_to_last(1).get())[0])\
                .delete()
            self.get_last_datapoint_date()


if __name__ == '__main__':
    credential = credentials.Certificate('wintergarden-ff60f-271493670cf3.json')
    initialize_app(credential=credential, options=db_config)
    ref = db.reference('/Log/')
    logging.basicConfig(filename='logs/log.txt', encoding='utf-8', level=logging.INFO)
    tz = pytz.timezone(os.environ['TZ'])
    alert_handler = AlertHandler(token=bot_config['token'], channel=bot_config['channel'],
                                 db_reference=ref, time_interval=40, timer_delay=1, tz=tz)
    # alert_handler = AlertHandler(token=bot_config['token'], channel=bot_config['test_channel'],
    #                              db_reference=ref, time_interval=2, timer_delay=0.5, tz=tz)
    alert_handler.start()
