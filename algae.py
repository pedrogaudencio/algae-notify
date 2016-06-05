from email.mime.text import MIMEText
import json
import os
import requests
import smtplib
import time

DATE = time.strftime("%Y_%m_%d")


class AlgaeNotify(object):
    def __init__(self, config):
        self._url = config.get('url')
        self._limits = config.get('limits')
        self._sensors = config.get('sensors')
        self._template = config.get('template')
        self._email = config.get('email')
        self._filename = '/'.join([DATE, DATE]) + '.json'
        self._chlorophyll = {}
        self._data = {}

    def get_roots(self):
        if not os.path.exists(DATE):
            os.makedirs(DATE)
            with open(self._filename, 'w') as f:
                json.dump({}, f)
            self._data = {}
        else:
            with open(self._filename) as f:
                self._data = json.load(f)

    def photosynthesis(self):
        page = requests.get(self._url)
        self._chlorophyll = json.loads(page.content)

    def within_bounds(self, sensor, value):
        return (self._limits.get(sensor).get('min') <= float(value) and
                float(value) <= self._limits.get(sensor).get('max'))

    def check_range(self):
        offbounds = []
        for sensor, value in self._chlorophyll.items():
            if not self.within_bounds(sensor, value):
                offbounds.append((sensor, value))
        return offbounds

    def store(self):
        timestamp = time.strftime("%Y_%m_%d_%H_%M_%S")
        with open(self._filename, 'w') as outfile:
            self._data[timestamp] = self._chlorophyll
            json.dump(self._data, outfile)

    def log(self, match={}):
        if match:
            body = ""
            for m in match:
                body += self._template.get('error').format(self._sensors[m[0]],
                                                           m[1])
        else:
            body = self._template.get('ok')

        self.notify(body.encode("utf-8"))

    def notify(self, body):
        msg = MIMEText(body)
        msg['Subject'] = self._email.get('subject')
        msg['From'] = self._email.get('from')
        msg['To'] = self._email.get('to')
        try:
            s = smtplib.SMTP('localhost', 1025)
            s.sendmail(msg['Subject'], msg['To'], msg.as_string())
        except Exception as e:
            print("Something went wrong:\n\n{}".format(e))

    def grow(self):
        self.get_roots()
        self.photosynthesis()
        match = self.check_range()
        self.store()
        self.log(match)


if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
        algae = AlgaeNotify(config)
        algae.grow()
