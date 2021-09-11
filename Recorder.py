#!/usr/bin/env python3

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
import logging

class Recorder(gr.hier_block2):
  def __init__(self, samp_rate=16E3, name="unnamed", save_dir=None, postscript=None):
    gr.hier_block2.__init__(self, "Recorder", 
      gr.io_signature(1, 1, gr.sizeof_float), gr.io_signature(1, 1, gr.sizeof_float))

    self.timeout = 18000
    self.save_dir = save_dir
    self.postscript = postscript
    self.record_squelch = analog.pwr_squelch_ff(-200, 0.1, 0, True)
    self.blocks_wavfile_sink = blocks.wavfile_sink("/dev/null", 1, samp_rate, 16)
    self.blocks_null_source = blocks.null_source(gr.sizeof_float*1)
    self.connect(self, (self.record_squelch, 0))
    self.connect((self.record_squelch, 0), (self.blocks_wavfile_sink, 0))
    self.connect((self.blocks_null_source, 0), self)
       
    thread = threading.Thread(target=self.timer_thread, 
      args=(name, self.save_dir, self.blocks_wavfile_sink, \
              self.record_squelch, self.postscript, self.timeout))
    thread.daemon = True
    thread.start()

  def timer_thread(self, name, save_dir, wavfile_sink, rec_squelch, postscript, timeout):

    file_open = False
    on_counter = 0
    off_counter = 0
    sql_open = False

    while True:
      if rec_squelch.unmuted():
        off_counter = 0
        if not sql_open:
          sql_open = True
          logging.info("%s open", name)
        if file_open:
          on_counter+=1
        else:
          tstamp = "_" + time.strftime("%Y%m%d-%H%M%S")
          start_time = time.time()
          file_name = save_dir + "/" + name + tstamp + ".wav"
          wavfile_sink.open(file_name)
          file_open = True
          on_counter = 0
          logging.info("Started new file %s ", file_name)
      else:
        if sql_open:
          sql_open = False
          logging.info("%s closed", name)
        if file_open:
          #close file if idle for 1min or open for <timeout> tenth-seconds
          if off_counter > 600 or on_counter > timeout:
            end_time = time.time()-(off_counter/10)
            if on_counter < timeout:
               logging.info("closing %s after %d seconds of inactivity", \
                      file_name, int(off_counter/10))
               logging.info("Total Activity %d seconds", \
                       (int(on_counter/10)))
            else:
               logging.info("closing %s after %d seconds of activity", \
                      file_name, int(on_counter/10))
            wavfile_sink.close()
            file_open = False
            #delete file if less then 4 seconds
            if on_counter < 40:
              logging.info("deleting %s with only %d seconds activity", \
                  file_name, int(on_counter/10))
              os.unlink(file_name)
            else:
              self.convert_file(file_name, save_dir, name, \
                      postscript, start_time, end_time)
          else:
            off_counter+=1

      time.sleep(0.1)

  def convert_file(self, old_filename, sdir, cname, postscript, stime, etime):
    
    os.putenv("TZ", "EST5EDT")
    new_file_name = sdir + "/" + cname + "/"
    new_file_name += time.strftime("%Y%m%d", time.localtime(stime))
    
    try:
      os.makedirs(new_file_name)
    except OSError:
      pass
    
    new_file_name += "/" + time.strftime("%H%M%S", time.localtime(stime))
    new_file_name += "_"
    new_file_name += time.strftime("%H%M%S", time.localtime(etime))
    new_file_name += ".mp3"
    subprocess.call(['lame', '--silent', old_filename, new_file_name])
    if postscript is not None:
       subprocess.call([postscript, old_filename, new_file_name])
    else:
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
  
  logging.basicConfig(format='%(asctime)s %(message)s', \
      datefmt='%m/%d/%Y %H:%M:%S', level=logging.DEBUG)
  
  tb = RecTest()
  tb.start()

  print("\nstarting test cycle ...\n")
  tb.mute.set_mute(False)
  print("test loop unmute: 10 second transmission")
  time.sleep(10)
    
  print("test loop mute: Quiet for 65 seconds")
  tb.mute.set_mute(True)
  time.sleep(65)
  
  print("test loop unmute: 3 second transmission")
  tb.mute.set_mute(False)
  time.sleep(3)
    
  print("test loop mute: Quiet for 65 seconds")
  tb.mute.set_mute(True)
  time.sleep(65)
  
  print("test loop unmute: 10 minute transmission")
  tb.mute.set_mute(False)
  time.sleep(600)
    
  print("test loop mute: Quiet for 10 seconds")
  tb.mute.set_mute(True)
  time.sleep(10)
  
  print("test loop unmute: 10 minute transmission")
  tb.mute.set_mute(False)
  time.sleep(600)
    
  print("test loop mute: Quiet for 15 seconds")
  tb.mute.set_mute(True)
  time.sleep(15)
  
  print("test loop unmute: 11 minute transmission")
  tb.mute.set_mute(False)
  time.sleep(660)
    
  print("test loop mute: Quiet for 40 seconds")
  tb.mute.set_mute(True)
  time.sleep(40)
  
  print("test loop unmute: 3 minute transmission")
  tb.mute.set_mute(False)
  time.sleep(180)
    
  print("test loop mute: Quiet for 70 seconds")
  tb.mute.set_mute(True)
  time.sleep(70)
   
  print("\ntest cycle complete\n")
  
  try:
    input('Press Enter to quit: ')
  except EOFError:
    pass
  tb.stop()
  tb.wait()
