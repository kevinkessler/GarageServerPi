import wiringpi
import threading
import multiprocessing
import time
"""
Had to spawn these off as processes, because wiringpi segfaults on the ISR when the MQTT thread is started,
or time.sleep is run in the same process
"""


class Button(multiprocessing.Process):

  def __init__(self, pin, edge_type, debounce_time, pull_resistor, topic, pipe):
    multiprocessing.Process.__init__(self)
    self.daemon = True
    self.pin = pin
    self.edge_type = edge_type
    self.debounce_time = debounce_time
    self.pull_resistor = pull_resistor
    self.topic = topic
    self.pipe = pipe
    self.timer = None
    self.pin_state = 0
    self.timer_target = 0

  def run(self):
    wiringpi.wiringPiSetup()

    wiringpi.pinMode(self.pin, wiringpi.GPIO.INPUT)
    wiringpi.pullUpDnControl(self.pin, getattr(wiringpi.GPIO, self.pull_resistor))
    wiringpi.wiringPiISR(self.pin, getattr(wiringpi.GPIO, self.edge_type), self._button_callback)

    t = threading.Thread(target=self._queue_thread)
    t.setDaemon(True)
    t.start()

    while True:
      wiringpi.delay(1000)

  def _timer_thread(self):
    while True:
      if self.timer_target < time.time():
        break

    self._timer_callback()

  def _button_callback(self):
    self.timer_target = time.time() + self.debounce_time
    if self.timer is None:
      self.pin_state = wiringpi.digitalRead(self.pin)
      self.timer = threading.Thread(target=self._timer_thread)
      self.timer.start()

  def _timer_callback(self):
    pin_value = wiringpi.digitalRead(self.pin)
    self.timer = None
    if self.pin_state == pin_value:
      self.pipe.send([self.topic, self._readString(self.pin_state)])

  def _readString(self, state):
      mes = "HIGH"
      if self.pin_state == wiringpi.GPIO.LOW:
        mes = "LOW"

      return mes

  def _queue_thread(self):
    while True:
      msg = self.pipe.recv()
      if isinstance(msg, str) and msg == '?':
        print("->")
        self.pipe.send([self.topic, self._readString(wiringpi.digitalRead(self.pin))])
        print("<-")

