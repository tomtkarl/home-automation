import threading
import urllib
import time
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from http.server import BaseHTTPRequestHandler, HTTPServer
from cgi import parse_header, parse_multipart

import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.INFO)

client = ModbusClient(method='rtu', port='/dev/ttyUSB0',
                      timeout=1, baudrate=9600)
client.connect()

UNIT = 0x1
MAX_TEMP = 23.6
MIN_TEMP = 17.0
POLL_INTERVAL_S = 1
temperature = 100.0
humidity = -100.0


def fetch_centigrade_and_humidity():
    global temperature, humidity
    rr = client.read_holding_registers(0, 4, unit=UNIT)
    temperature = rr.registers[0] / 10.0
    humidity = rr.registers[1] / 10.0


class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(f"""<html>
                <body>
                <h1>Temperature (centigrade)</h1>
                <p>Actual: {temperature:10.4}
                 <form method="post">
                    <label for="max_temp">Max:\t</label>
                    <input name="max_temp" id="max_temp"
                           type="text"
                           value="{MAX_TEMP}" />
                    <br />
                    <label for="min_temp">Min:\t</label>
                    <input name="min_temp" id="min_temp"
                           type="text"
                           value="{MIN_TEMP}" />
                    <br />
                    <input type="submit" value="Update" />
                </form>
                </p>
                <h1>Humidity (percentage)</h1>
                <p>Actual {humidity:10.4}%</p>

                <form method="post">
                    <label for="poll_interval">Poll interval (s):</label>
                    <input name="poll_interval_s" id="poll_interval_s"
                           type="text"
                           value="{POLL_INTERVAL_S}" />
                    <input type="submit" value="Update" />
                </form>

               </body>
                </html>""".encode('utf-8'))

    def do_HEAD(self):
        self._set_headers()

    def parse_POST(self):
        ctype, pdict = parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            postvars = parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            postvars = urllib.parse.parse_qs(
                    self.rfile.read(length),
                    keep_blank_values=1)
        else:
            postvars = {}
        return postvars

    def do_POST(self):
        post_data = self.parse_POST()
        global MIN_TEMP, MAX_TEMP, POLL_INTERVAL_S
        if b'min_temp' in post_data:
            MIN_TEMP = float(post_data[b'min_temp'][0])
        if b'max_temp' in post_data:
            MAX_TEMP = float(post_data[b'max_temp'][0])
        if b'poll_interval_s' in post_data:
            POLL_INTERVAL_S = float(post_data[b'poll_interval_s'][0])
        self.do_GET()


def run_httpd(server_class=HTTPServer, handler_class=S, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd...')
    httpd.serve_forever()


def fetch_and_test_temparature():
    while True:
        logging.debug('Fetching temp and humidity')
        fetch_centigrade_and_humidity()
        global temperature
        if temperature >= MAX_TEMP:
            print(f"Too hot! {temperature:10.4} degrees")
        if temperature <= MIN_TEMP:
            print(f"Too cold! {temperature:10.4} degrees")
        time.sleep(POLL_INTERVAL_S)


t = threading.Thread(target=fetch_and_test_temparature)
t.start()
run_httpd()
