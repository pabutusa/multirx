# multirx
Receive Multiple channels in the bandwidth of an SDR converter (RTL-SDR) optionally recording or streaming to an ICECAST server 

Originally designed to allow Emergency Service Volunteers (Fire, EMT, ...) to
monitor radio channels over internet connected devices and review prior calls.

This was my first attempt at doing anything with Python and GNURadio ... so all
standard disclaimers apply. 

I have also shamelessly used the HAM2MON project as inspiration and general
structure. While HAM2MON is a great curses based app for monitoring ALL activity
in a given bandwidth MULTIRX was designed as a server application to stream and 
record specific channels. 

This is still a work in progress. There is LOTS of opportunity for improvement
in handling error cases or improving performance. Constructed comments always
appreciated. Special thanks to my orginal BETA (more like ALPHA) testers: KC2SJT,
KC2SJU, and KC2VWI.

DEPENDANCIES (lots I'm forgetting)
- GNURADIO (I like to build from source) 
