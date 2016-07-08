from datetime import datetime
from email.mime.text import MIMEText
import json
from operator import div, eq
import os
import requests
import smtplib
from time import sleep

DATE = str(datetime.today().date()).replace('-', '_')


class AlgaeNotify(object):
    def __init__(self, config):
        self._url = config.get('url')
        self._limits = config.get('limits')
        self._sensors = config.get('sensors')
        self._template = config.get('template')
        self._email = config.get('email')
        self._filename = '/'.join([DATE, DATE]) + '.json'
        self._last_email_timestamp = datetime.now()
        self._run_interval = config.get('interval').get('running') * 60
        self._stalled_length = div(config.get('interval').get('stalled'),
                                   self._run_interval)
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

    def stalling(self):
        """
        1. get interval
        2. get all values within that interval
        3. check if they're all the same
        4. get time in seconds (from 1970?) and calculate
        5. write backwards compability for previous dates
        6. if it's simple and fast like
           self._chlorophyll.values()[:5].replace('_', ',')
           just run everything like this, otherwise should store in different
           format
        7. do log() more generic (self, fails, error='match', send=False)
        8. log(fails, why='offline')
        """
        measurements = self._chlorophyll.values()[:self._stalled_length]
        set_m1 = set(measurements.pop())
        fails = all(map(lambda m: eq(len(set(m) | set_m1),
                                     len(set_m1)),
                        measurements))
        self.log(fails, why='offline')

    def store(self):
        dt = str(datetime.now())[:19].replace('-', '_').replace(':', '_')
        with open(self._filename, 'w') as outfile:
            self._data[dt] = self._chlorophyll
            json.dump(self._data, outfile)

    def log(self, fails, why='match', send=False):
        body = "{}\n\n".format(str(datetime.now())[:19])
        if fails:
            if why == 'match':
                for fail in fails:
                    body += self._template.get('error').get(why).format(
                        self._sensors[fail[0]],
                        fail[1])
            elif why == 'offline':
                body += self._template.get('error').get(why)
        elif send:
            body += self._template.get('ok')

        self.notify(body.encode("utf-8")) if fails or send else None

    def notify(self, body):
        msg = MIMEText(body)
        msg['Subject'] = self._email.get('subject')
        msg['From'] = self._email.get('from')
        to = self._email.get('to')
        msg['To'] = ', '.join(to) if len(to) > 1 else to[0]
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            server.login(self._email.get('from'), self._email.get('password'))
            server.sendmail(msg['Subject'], to, msg.as_string())
            server.quit()
            self.update_clock()
        except Exception as e:
            print("Something went wrong:\n\n{}".format(e))

    def update_clock(self):
        self._last_email_timestamp = datetime.now()

    def delay(self):
        sleep(self._interval)

    def grow(self):
        self.get_roots()
        self.photosynthesis()
        failures = self.check_range()
        self.store()
        self.log(failures)
        self.delay()


if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
        algae = AlgaeNotify(config)
        while True:
            algae.grow()
