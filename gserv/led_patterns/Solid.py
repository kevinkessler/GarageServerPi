import threading


class SolidPattern():
  def __init__(self, parent, pattern_name, config):
    self.parent = parent
    self.config = config
    self.pattern_name = pattern_name
    self.patterns = {
      "BLANK": [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]
    }
    self.timer = None
    self.current_color = self.patterns[self.pattern_name]
    self.timer_period = 60
    self.stop_run = False

  def start(self):
    self._write_leds()

  def stop(self):
    self.stop_run = True
    if self.timer:
      self.timer.cancel()

  def _write_leds(self):
    if self.stop_run:
      return

    self.parent.writeSPIData(self.current_color)
    self.timer = threading.Timer(self.timer_period, self._write_leds).start()
