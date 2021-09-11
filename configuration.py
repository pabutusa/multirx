#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import sys

class Configuration:
   def __init__(self, filename):
      try:
         tree = ET.parse(filename)
      except IOError:
         sys.exit("configuration file not found.")

      root = tree.getroot()

      self._serial = root.find('system/serial')
      self._gain = root.find('system/gain')
      self._freq_corr = root.find('system/freq_corr')
      self._save_dir = root.find('system/save_dir')
      self._ice_host = root.find('system/ice_host')
      self._ice_port = root.find('system/ice_port')
      self._ice_auth = root.find('system/ice_auth')
   
      # Create an array of tuples with the channel info
      self.channel = []
      for i in root.findall('channel'):
         frequency = int(float(i.find('frequency').text)*1E6)
         key = i.find('key').text
         description = i.find('description').text
         ctcss = float(i.find('ctcss').text)
         _postscript = i.find('postscript')
         if _postscript is not None:
             postscript = _postscript.text
         else:
             postscript = None
         _squelch = i.find('squelch')
         if _squelch is not None:
             squelch = int(_squelch.text)
         else:
             squelch = 20

         self.channel.append((key, frequency, description, ctcss, postscript, squelch))

      # Find the highest Channel
      self.high = 0
      for j in self.channel:
         if j[1] > self.high:
            self.high = j[1]
      
      # Find the lowest Channel
      self.low = float("inf")
      for j in self.channel:
         if j[1] < self.low:
            self.low = j[1]

      #Calculate the span from low to high
      self.width = self.upper() - self.lower()

      #Calculate the center of the span
      self.middle = self.lower() + (self.span()/2)

      
   def ice_host(self):
       if self._ice_host is not None:
          return self._ice_host.text
       else:
          return None

   def ice_port(self):
       if self._ice_port is not None:
          return int(self._ice_port.text)
       else:
          return None

   def ice_auth(self):
       if self._ice_auth is not None:
          return self._ice_auth.text
       else:
          return None

   def save_dir(self):
       if self._save_dir is not None:
          return self._save_dir.text
       else:
          return None

   def freq_corr(self):
       if self._freq_corr is not None:
          return int(self._freq_corr.text)
       else:
          return int(0)

   def gain(self):
       if self._gain is not None:
           return int(self._gain.text)
       else:
           return int(0)

   def serial(self):
       return self._serial.text

   def upper(self):
      return self.high

   def lower(self):
      return self.low

   def center(self):
      return self.middle

   def span(self):
      return self.width

if __name__ == '__main__':

   config = Configuration('receiver2.xml')

   high = config.upper()
   low = config.lower()
   center = config.center()
   span = config.span()
   ser_num = config.serial()
   save_dir = config.save_dir()

   print("Device serial#: %s" % ser_num)
   print("Save Directory: %s" % save_dir)
   print("Gain=%d, Freq_Correction=%d" % 
           (config.gain(), config.freq_corr()))
   print("ice_host: %s, ice_port: %d, ice_auth: %s" % (config.ice_host(), 
           config.ice_port(), config.ice_auth()))
   print("high=%d low=%d" % (high, low))
   print("center=%d" % center)
   print("span=%d" % span)
   for i in config.channel:
      print(i)
