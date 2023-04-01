FROM python:3.10.6
RUN pip install firebase_admin python-telegram-bot pytz
ADD . .
ENV TZ="Europe/Moscow"
CMD ["python", "./main.py"]