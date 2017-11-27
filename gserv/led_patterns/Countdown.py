import threading
import time

'''
Create a pattern on the LED for a 10 minute (600 seconds) countdown.  Start with all yellow.  Every second, spin a blank LED
around the ring.  Every 24 seconds, bump the colors up, one led at a time from yellow to red. 3 steps from yellow to red X 8 LEDs
makes 24 steps.  24 Steps X 24 seconds is 576 seconds, but since I want the last step of RED_CLOCKWISE to last 30 seconds (to go
with the piezoelectric speaker), the last iteration is stopped 6 seconds early at 570 seconds.
'''


class CountdownPattern():
  def __init__(self, parent, pattern_name, config):
    self.parent = parent
    self.config = config
    self.pattern_name = pattern_name
    self.color_values = [[0x42, 0x80, 0x00], [0x42, 0x80, 0x00], [0x42, 0x80, 0x00], [0x42, 0x80, 0x00],
        [0x42, 0x80, 0x00], [0x42, 0x80, 0x00], [0x42, 0x80, 0x00], [0x42, 0x80, 0x00]]
    self.timer = None
    self.timer_period = 0.1
    self.stop_run = False

    self.color_count = 0
    self.counter = 0
    self.steps = [0x38, 0x28, 0x00]
    self.step_idx = 0
    self.spin_count = 0
    self.second_count = 0
    self.time = 0

    self.top_led = self.config['top_led']
    self.last_led = self.top_led - 1
    if self.last_led < 0:
      self.last_led = 7

  def start(self):
    self._write_leds()

  def stop(self):
    self.stop_run = True
    if self.timer:
      self.timer.cancel()

  def _write_leds(self):
    if self.stop_run:
      return

    if self._spin():
      '''
      Every 24 seconds, crawl the color one more step. When there is 30 seconds left, turn the whole
      display to RED_CLOCKWISE
      '''
      if self.second_count % 24 == 0 or self.second_count == 570:
        self._color_change()
        self.parent.writeSPIData(self.color_values)

    self.timer = threading.Timer(self.timer_period, self._write_leds).start()

  '''
  Change the colors around the ring from yellow, 2 shades or orange to red.  When the final LED is set to red, 
  change the pattern to a spinning RED_CLOCKWISE 
  '''
  def _color_change(self):
      led = self.color_count + self.top_led
      if led > 7:
        led -= 8

      if self.color_count == 0 and self.color_values[self.last_led][0] == 0x00:
        self.parent.change_pattern("RED_CLOCKWISE")
        return

      self.color_values[led][0] = self.steps[self.step_idx]

      self.color_count += 1
      if self.color_count == 8:
          self.color_count = 0
          self.step_idx += 1

  '''
  Spin a blank LED around the circle for a one second timer.  Returns True when the 1 second spin is complete, and there should
  be a check for whether the colors should be rotated
  '''
  def _spin(self):
    led_spin = self.spin_count + self.top_led
    if led_spin > 7:
      led_spin -= 8

    # Start of the 1 seconds spin, start timer
    if self.spin_count == 0:
      self.time = time.time()

    # Blank LED unless it is the last spin, so turn it on
    temp_value = self.color_values[led_spin]
    if self.spin_count != 8:
      self.color_values[led_spin] = [0x00, 0x00, 0x00]

    self.parent.writeSPIData(self.color_values)
    self.color_values[led_spin] = temp_value

    self.timer_period = 0.05
    self.spin_count += 1

    if self.spin_count != 9:
      return False

    # Wait the remaing part of the second before starting the spin again
    self.timer_period = 1.0 - (time.time() - self.time)
    self.time = time.time()
    self.spin_count = 0
    self.second_count += 1

    return True
