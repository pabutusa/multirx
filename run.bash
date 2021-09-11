#!/bin/bash
cd /home/roschews/sdr/multirx2
while true
do 
   ./multirx_nogui.py receiver2.xml
   sleep 60
   mv wav/*.wav wav/partial
done
