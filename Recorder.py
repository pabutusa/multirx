#!/usr/bin/env python2

from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
import threading
import subprocess
import time
import os

class Recorder(gr.hier_block2):
  def __init__(self, samp_rate=16E3, name="unnamed"):
    gr.hier_block2.__init__(self, "Recorder", 
      gr.io_signature(1, 1, gr.sizeof_float), gr.io_signature(1, 1, gr.sizeof_float))
    self.record_squelch = analog.pwr_squelch_ff(-200, 0.1, 0, True)
    self.blocks_wavfile_sink = blocks.wavfile_sink("/dev/null", 1, samp_rate, 16)
    self.blocks_null_source = blocks.null_source(gr.sizeof_float*1)
    self.connect(self, (self.record_squelch, 0))
    self.connect((self.record_squelch, 0), (self.blocks_wavfile_sink, 0))
    self.connect((self.blocks_null_source, 0), self)
       
    thread = threading.Thread(target=self.timer_thread, 
      args=(name, self.blocks_wavfile_sink, self.record_squelch))
    thread.daemon = True
    thread.start()

  def timer_thread(self, name, wavfile_sink, rec_squelch):
    self.file_open = False
    self.on_counter = 0
    self.off_counter = 0
    self.save_dir = 'wav'
    self.verbose = False
    while True:
      if rec_squelch.unmuted():
	self.off_counter = 0
	if self.file_open:
	  self.on_counter+=1
	else:
	  self.tstamp = "_" + time.strftime("%Y%m%d-%H%M%S")
	  self.start_time = time.time()
	  self.file_name = self.save_dir + "/" + name + self.tstamp + ".wav"
	  wavfile_sink.open(self.file_name)
	  self.file_open = True
	  self.on_counter = 0
	  if self.verbose:
	    print "Started new file %s " % self.file_name
      else:
	if self.file_open:
	  if self.off_counter > 600: #close file if idle for 1min
	    self.end_time = time.time()-(self.off_counter/10)
	    if self.verbose:
	      print "closing %s after %d seconds of inactivity" % \
		      (self.file_name, int(self.off_counter/10))
	    if self.verbose:
	      print "Total Activity %d seconds" % (int(self.on_counter/10))
	    wavfile_sink.close()
	    self.file_open = False
	    if self.on_counter < 40: #delete file if less then 4 seconds
	      if self.verbose:
		print "deleting %s with only %d seconds activity" % \
		  (self.file_name, int(self.on_counter/10))
	      os.unlink(self.file_name)
	    else:
	      self.convert_file(self.file_name, self.save_dir, name, self.start_time, self.end_time)
	  else:
	    self.off_counter+=1
	    if self.on_counter >36000: #close file because it's big
	      wavfile_sink.close()
	      file_open = False
	      self.convert_file(self.file_name, self.save_dir, name, self.start_time, self.end_time)

      time.sleep(0.1)

  def convert_file(self, old_filename, sdir, cname, stime, etime):
    
    os.putenv("TZ", "EST5EDT")
    self.new_file_name = sdir + "/" + cname + "/"
    self.new_file_name += time.strftime("%Y%m%d", time.localtime(stime))
    
    try:
      os.makedirs(self.new_file_name)
    except OSError:
      pass
    
    self.new_file_name += "/" + time.strftime("%H%M%S", time.localtime(stime))
    self.new_file_name += "_"
    self.new_file_name += time.strftime("%H%M%S", time.localtime(etime))
    self.new_file_name += ".mp3"
    subprocess.call(['lame', '--silent', old_filename, self.new_file_name])
    os.unlink(old_filename)

class RecTest(gr.top_block):
  def __init__(self):
    gr.top_block.__init__(self, "RecTest")

    samp_rate = 16000
  
    self.source = analog.sig_source_f(samp_rate, analog.GR_SIN_WAVE, 1000, 1, 0)
    self.recorder = Recorder(samp_rate, "testname")
    self.throttle = blocks.throttle(gr.sizeof_float*1, samp_rate,True)
    self.mute = blocks.mute_ff(bool(False))
      
    self.connect((self.source, 0), (self.throttle, 0), (self.mute, 0), (self.recorder, 0))

if __name__ == '__main__':
  tb = RecTest()
  tb.start()

  print "test loop start"
  time.sleep(10)
    
  print "test loop mute"
  tb.mute.set_mute(True)
  time.sleep(65)
  
  print "test loop unmute"
  tb.mute.set_mute(False)
  time.sleep(3)
    
  print "test loop mute"
  tb.mute.set_mute(True)
  time.sleep(65)
   
  print "test loop complete"
  
  try:
    raw_input('Press Enter to quit: ')
  except EOFError:
    pass
  tb.stop()
  tb.wait()
