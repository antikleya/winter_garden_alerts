from firebase_admin import db, initialize_app, credentials
from datetime import datetime
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


class AlertHandler:
    def __init__(self, token: str, channel: str, db_reference, time_interval: int = 40, timer_delay: float = 5,
                 tz = pytz.timezone('Europe/Moscow')):
        self.bot = telegram.Bot(token)
        self.db_reference = db_reference
        self.channel = channel
        self.alert_flag = False
        self.time_interval = time_interval
        self.timer_delay = int(timer_delay * 60)
        self.tz = tz

    def get_log_message(self, difference: int, send_alert: bool) -> str:
        return f"[{datetime.now(tz=self.tz).strftime('%H:%M %d/%m/%Y')}] {'ALERT ' if self.alert_flag else ''}" \
               f"Current difference is {difference}. {'ALERT SENT.' if send_alert else ''}"

    def get_last_datapoint_date(self) -> datetime:
        snapshot = self.db_reference.order_by_child('timestamp').limit_to_last(1).get()
        date = datetime.fromtimestamp(list(snapshot.values())[0]['timestamp'] - 10800, tz=self.tz)
        return date

    async def alert(self, difference: int):
        async with self.bot:
            await self.bot.send_message(self.channel, f"[ALERT] No data sent for {difference} minutes")

    def monitor(self):
        now = datetime.now(tz=self.tz)
        last_datapoint_time = self.get_last_datapoint_date()
        difference = now - last_datapoint_time
        diff_in_minutes = difference.seconds // 60
        send_alert = False
        print(diff_in_minutes)

        if (diff_in_minutes > self.time_interval) and (not self.alert_flag):
            asyncio.run(self.alert(difference=diff_in_minutes))
            send_alert = True
            self.alert_flag = True
        elif diff_in_minutes < self.time_interval:
            self.alert_flag = False

        logging.info(self.get_log_message(diff_in_minutes, send_alert))

    def start(self):
        timer = RepeatTimer(self.timer_delay, self.monitor)
        timer.start()
        x = ''
        try:
            while 1:
                pass
        except:
            timer.cancel()


if __name__ == '__main__':
    credential = credentials.Certificate('wintergarden-ff60f-271493670cf3.json')
    initialize_app(credential=credential, options=db_config)
    ref = db.reference('/Log/')
    logging.basicConfig(filename='logs/log.txt', encoding='utf-8', level=logging.INFO)
    tz = pytz.timezone(os.environ['TZ'])
    alert_handler = AlertHandler(token=bot_config['token'], channel=bot_config['test_channel'],
                                 db_reference=ref, time_interval=2, timer_delay=0.5, tz=tz)
    alert_handler.start()
