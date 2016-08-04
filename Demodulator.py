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
import math
import numpy as np
import osmosdr
import time
import os
import os.path
import string


class Demodulator(gr.hier_block2):
    def __init__(self, samp_rate=2E6, demod_bb_freq=0, squelch=50, tone=0):
       gr.hier_block2.__init__(self, "Demodulator",
          gr.io_signature(1, 1, gr.sizeof_gr_complex),
          gr.io_signature(1, 1, gr.sizeof_short))

       self.initial_decim = initial_decim = 5
       self.samp_ratio = samp_ratio = samp_rate/1E6
       self.final_rate = final_rate = samp_rate/initial_decim**2/int(samp_rate/1E6)
       self.variable_low_pass_filter_taps_0 = firdes.low_pass(1.0, 1, 0.090, 0.010, firdes.WIN_HAMMING, 6.76)
       self.variable_low_pass_filter_taps_1 = firdes.low_pass(1.0, samp_rate/25, 12.5E3, 1E3, firdes.WIN_HAMMING, 6.76)
       self.variable_low_pass_filter_taps_2 = firdes.low_pass(1.0, final_rate, 3500, 500, firdes.WIN_HAMMING, 6.76)
       self.variable_band_pass_filter_taps_3 = firdes.band_pass(1.0, 16E3, 500, 3000, 100, firdes.WIN_HAMMING, 6.76)
       self.squelch_dB = squelch_dB = -squelch
       self.ctcss_freq = tone
       self.ctcss_samp_rate = int(samp_rate/((self.initial_decim**2)*(samp_rate/1E6)))
       self.final_decim = final_decim = int(samp_rate/1E6)

       self.freq_xlating_fir_filter = filter.freq_xlating_fir_filter_ccc(
           initial_decim, (self.variable_low_pass_filter_taps_0), demod_bb_freq, samp_rate)

       self.fir_filter_0 = filter.fir_filter_ccc(initial_decim, (self.variable_low_pass_filter_taps_0))
       self.fir_filter_0.declare_sample_delay(0)

       self.fir_filter_1 = filter.fir_filter_ccc(int(samp_rate/1E6), (self.variable_low_pass_filter_taps_1))
       self.fir_filter_1.declare_sample_delay(0)

       self.analog_pwr_squelch_0 = analog.pwr_squelch_cc(squelch_dB, 0.1, 0, False)

       self.quadrature_demod = analog.quadrature_demod_cf(1)

       self.analog_ctcss_squelch_0 = analog.ctcss_squelch_ff( \
            self.ctcss_samp_rate, self.ctcss_freq, .01, 0, 0, False)
            
       self.fir_filter_2 = filter.fir_filter_fff(initial_decim, (self.variable_low_pass_filter_taps_2))
       self.fir_filter_2.declare_sample_delay(0)

       self.pfb_arb_resampler_xxx_0 = \
           pfb.arb_resampler_fff(16E3/float(final_rate/5), taps=None, flt_size=32)
       self.pfb_arb_resampler_xxx_0.declare_sample_delay(0)
       
       self.band_pass_filter = filter.fir_filter_fff(1, (self.variable_band_pass_filter_taps_3))

       self.float_to_short = blocks.float_to_short(scale=32768.0)

       self.connect(self, (self.freq_xlating_fir_filter, 0))
       self.connect((self.freq_xlating_fir_filter, 0), (self.fir_filter_0, 0))    
       self.connect((self.fir_filter_0, 0), (self.fir_filter_1, 0))
       
       self.connect((self.fir_filter_1, 0), (self.analog_pwr_squelch_0, 0))    
       self.connect((self.analog_pwr_squelch_0, 0), (self.quadrature_demod, 0))

       if self.ctcss_freq == 0:
          self.connect((self.quadrature_demod, 0), (self.fir_filter_2, 0))
       else:
	  self.connect((self.quadrature_demod, 0), (self.analog_ctcss_squelch_0, 0))
	  self.connect((self.analog_ctcss_squelch_0, 0), (self.fir_filter_2, 0))
	  
       self.connect((self.fir_filter_2, 0), (self.pfb_arb_resampler_xxx_0, 0))
       self.connect((self.pfb_arb_resampler_xxx_0, 0), (self.band_pass_filter, 0))
       self.connect((self.band_pass_filter, 0), (self.float_to_short, 0))
       self.connect((self.float_to_short, 0), self)
        	
class examplerx(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "MULTIRX testing")

        self.center_freq = 162475000
        self.squelch = -100


        self.samp_rate = samp_rate = 1E6
        self.gain_db = gain_db = 30
        
        self.osmosdr_source = osmosdr.source( args="numchan=" + str(1) + " " + "rtl" )
        self.osmosdr_source.set_sample_rate(samp_rate)
        self.osmosdr_source.set_center_freq(self.center_freq, 0)
        self.osmosdr_source.set_freq_corr(69, 0) #move this to option
        self.osmosdr_source.set_dc_offset_mode(0, 0)
        self.osmosdr_source.set_iq_balance_mode(0, 0)
        self.osmosdr_source.set_gain_mode(False, 0)
        self.osmosdr_source.set_gain(gain_db, 0)
        self.osmosdr_source.set_if_gain(20, 0)
        self.osmosdr_source.set_bb_gain(20, 0)
        self.osmosdr_source.set_antenna("", 0)
        self.osmosdr_source.set_bandwidth(samp_rate*0.8, 0)
	
	self.audio_sink = audio.sink(16000, "", True)
	self.blocks_short_to_float = blocks.short_to_float(1, 32768)

        self.demod_bb_freq = 0
        self.ctcss_freq = 0
        self.demod = Demodulator(self.samp_rate)
        self.connect((self.osmosdr_source, 0), (self.demod, 0))
        self.connect((self.demod, 0), (self.blocks_short_to_float, 0))
        self.connect((self.blocks_short_to_float, 0), (self.audio_sink, 0))    

if __name__ == '__main__':
   tb = examplerx()
   tb.start()
   try:
      raw_input('Press Enter to quit: ')
   except EOFError:
      pass
   tb.stop()
   tb.wait()
	    
	    