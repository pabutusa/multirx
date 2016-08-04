#!/bin/bash

while true
do 
   ./multirx_nogui.py -s 45 receiver2.xml
   sleep 60
   mv wav/*.wav wav/partial
done
