#!/usr/bin/env python2

from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.filter import pfb
from optparse import OptionParser
import sys
import math
import numpy as np
import osmosdr
import time
import os
import os.path
import subprocess
import threading
import select
import fcntl
import socket
import string
from base64 import b64encode
import configuration
import Recorder
import Demodulator
import logging
        	
class multirx_example(gr.top_block):
    def __init__(self, filename, options):
        gr.top_block.__init__(self, "MULTIRX testing")

        self.config = configuration.Configuration(filename)
        self.center_freq = center_freq = self.config.center()
        self.squelch = options.squelch

        print "high=%d low=%d span=%d" % (self.config.upper(), 
           self.config.lower(), (self.config.upper() - self.config.lower()))
        print "center=%d" % self.center_freq

        self.samp_rate = samp_rate = 1E6
        self.gain_db = gain_db = 30
        
        self.osmosdr_source = osmosdr.source( args="numchan=" + str(1) + " " + "rtl=00000001" )
        self.osmosdr_source.set_sample_rate(samp_rate)
        self.osmosdr_source.set_center_freq(center_freq, 0)
        self.osmosdr_source.set_freq_corr(69, 0) #move this to option
        self.osmosdr_source.set_dc_offset_mode(0, 0)
        self.osmosdr_source.set_iq_balance_mode(0, 0)
        self.osmosdr_source.set_gain_mode(False, 0)
        self.osmosdr_source.set_gain(gain_db, 0)
        self.osmosdr_source.set_if_gain(20, 0)
        self.osmosdr_source.set_bb_gain(20, 0)
        self.osmosdr_source.set_antenna("", 0)
        self.osmosdr_source.set_bandwidth(samp_rate*0.8, 0)
        
        self.blocks_adder = blocks.add_vss(1)

        for self.i, self.entry in enumerate(self.config.channel):
            self.demod_bb_freq = self.entry[1] - self.center_freq
            self.ctcss_freq = self.entry[3]
            self.demod = Demodulator.Demodulator(self.samp_rate, \
		self.demod_bb_freq, self.squelch, self.ctcss_freq)
            self.fname = self.setup_upstream_pipe(self.entry[0], self.entry[2])
            self.file_sink = blocks.file_sink(gr.sizeof_short*1, self.fname, True)
            self.connect((self.osmosdr_source, 0), (self.demod, 0), (self.file_sink, 0))    
	    self.connect((self.demod, 0), (self.blocks_adder, self.i))
            self.rec = Recorder.Recorder(16000, self.entry[0])
            self.connect((self.demod, 0), (blocks.short_to_float(1, 32768), 0), (self.rec, 0))
            time.sleep(1) #space things out a bit
        
	self.fname = self.setup_upstream_pipe("multiplex", "Multiplex Channel")
        self.file_sink = blocks.file_sink(gr.sizeof_short*1, self.fname, True)
        self.connect((self.blocks_adder, 0), (self.file_sink, 0))

        if options.local:
          self.audio_sink = audio.sink(16000, "", True)
          self.blocks_short_to_float = blocks.short_to_float(1, 32768)
	  self.connect((self.blocks_adder, 0), (self.blocks_short_to_float, 0), (self.audio_sink, 0))
     

    def setup_upstream_pipe(self, key, description):
        fname = "pipe-%s.raw" % key

        # create a pipe
        try:
            os.unlink(fname)
        except OSError:
            pass

        os.mkfifo(fname)

        samplerate = 16
        bitrate = 16
        bitwidth = 16
        cmd = ['lame',
           '--bitwidth', str(bitwidth),
           '-b', str(bitrate),
           '-m', 'm', # mode mono
           '-r', # raw samples
           '-s', str(samplerate), # sample rate
           '--signed', '--little-endian',
           '--flush', # flush as soon as possible
           '--silent', # less verbose
           '--scale', '1.0',
           fname, '-']

        # maximum bufsize - lame is configured to flush quicker, anyway
        bufsize = 2048
        pipe = subprocess.Popen(cmd, bufsize=bufsize, stdout=subprocess.PIPE).stdout
        # make pipe non-blocking
        fl = fcntl.fcntl(pipe, fcntl.F_GETFL)
        fcntl.fcntl(pipe, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        # set up a thread to read from the pipe
        thread = threading.Thread(target=self.upstream_thread, 
            args=(key, description, pipe, samplerate, bitrate))
        thread.daemon = True
        thread.start()

        return fname

    def upstream_thread(self, key, description, pipe, samplerate, bitrate):
        """
        Read mpeg data stream from pipe, upload to server with low latency
        """
        global error_count
        # TODO: error handling, never fail - retry and rewire
        poll = select.poll()
        poll.register(pipe, select.POLLIN|select.POLLERR)
        
        ice = None
        last_connect = 0
        
        while True:
            r = poll.poll(1000)
            if len(r) < 1:
                logging.info("%s ... poll timeout", key)
                error_count+=1
                continue
                
            fd, ev = r[0]
            d = pipe.read(4096)
            #print "read %d" % len(d)
            
            if ice == None and time.time() - last_connect > 4:
                # Connect to icecast
                logging.info("%s ... connecting ...", key)
                last_connect = time.time()
                try:
                    ice = self.icecast_connect(key, description, samplerate, bitrate)
                    logging.info("%s ... connected!", key)
                except Exception, e:
                    logging.info("... connect failed: %r", e)
                    ice = None
            
            if ice != None:
                try:
                    ice.send(d)
                except Exception:
                    try:
                        ice.close()
                        logging.info("%s ... disconnected!", key)
                    except Exception:
                        pass
                    ice = None

            
    def icecast_connect(self, key, description, samplerate, bitrate):
        """
        Connect to icecast
        """
        
        mountpoint = "/%s.mp3" % key

        def request_format(request, line_separator="\n"):
            return line_separator.join(["%s: %s" % (key, str(val)) for (key, val) in request.items()])
        
        host = 'aws.pabut.org'
        port = 8000
            
        logging.info("%s connecting %s:%d", key, host, port)
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.sendall("SOURCE %s ICE/1.0\n%s\n%s\n\n" % (
            mountpoint,
            request_format({
                'content-type': 'audio/mpeg',
                'Authorization': 'Basic ' + b64encode("source:" + 'bigtruck'),
                'User-Agent': "multirx"
            }),
            request_format({
                'ice-name': key,
                'ice-genre': 'Radio',
                'ice-bitrate': bitrate,
                'ice-private': 0,
                'ice-public': 0,
                'ice-description': description,
                'ice-audio-info': "ice-samplerate=%d;ice-bitrate=%d;ice-channels=1" %
                    (samplerate, bitrate),
		'ice-url': "http://%s:%d/%s.mp3" % (host, port, key)
            })
        ))
        
        response = s.recv(4096)
        if len(response) == 0:
            raise "No response from icecast server"
        
        if response.find(r"HTTP/1.0 200 OK") == -1:
            raise "Server response: %s" % response
        
        return s
        
if __name__ == '__main__':
   parser=OptionParser(option_class=eng_option)
   parser.add_option("-v", "--verbose", action="store_true", help="verbose")
   parser.add_option("-s", "--squelch", type="int", help="squelch")
   parser.add_option("-l", "--local", action="store_true", help="local monitor")
   parser.add_option("-m", "--multiplex", action="store_true", help="multiplex stream")
   (options, args) = parser.parse_args()

   if len(args) != 1:
      parser.print_help()
      sys.exit(1)
   
   logging.basicConfig(format='%(asctime)s %(message)s', \
      datefmt='%m/%d/%Y %H:%M:%S', level=logging.DEBUG)
   error_count = 0
   tb = multirx_example(args[0], options)
   tb.start()
   
   timeout = 5
   print "Press Enter to quit: "
   rlist, _, _ = select.select([sys.stdin], [], [], timeout)
   while not rlist:
     rlist, _, _ = select.select([sys.stdin], [], [], timeout)
     if error_count > 20:
       logging.info("Error count exceeded, restarting receivers.")
       break
      
   print "Exit Requested."
   tb.stop()
   tb.wait()
