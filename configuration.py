#!/usr/bin/env python2

import xml.etree.ElementTree as ET
import sys

class Configuration:
   def __init__(self, filename):
      try:
         self.tree = ET.parse(filename)
      except IOError:
         sys.exit("configuration file not found.")

      self.root = self.tree.getroot()
   
      self.channel = []
      for self.i in self.root.findall('channel'):
         self.frequency = int(float(self.i.find('frequency').text)*1E6)
         self.key = self.i.find('key').text
         self.description = self.i.find('description').text
         self.ctcss = float(self.i.find('ctcss').text)
         self.x = (self.key, self.frequency, self.description, self.ctcss)
         self.channel.append(self.x)

      self.high = 0
      for self.j in self.channel:
         if self.j[1] > self.high:
            self.high = self.j[1]
      
      self.low = float("inf")
      for self.j in self.channel:
         if self.j[1] < self.low:
            self.low = self.j[1]
      
      self.middle = self.lower() + ((self.upper() - self.lower())/2)

      
   def upper(self):
      return self.high

   def lower(self):
      return self.low

   def center(self):
      return self.middle


if __name__ == '__main__':

   config = Configuration('receiver.xml')

   high = config.upper()
   low = config.lower()
   center = config.center()

   print "high=%d low=%d" % (high, low)
   print "center=%d" % center
   for i in config.channel:
      print i
      
   




