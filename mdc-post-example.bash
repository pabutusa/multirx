#!/bin/bash
SAVE_DIR=/var/www/html/wav
NEWFILE=/home/user/sdr/multirx2/save/$(basename $1 .wav).raw
sox $1 -b 16 -e signed-integer -r16000 -t raw $NEWFILE
rm $1 
echo "$(date) $1 $2 $NEWFILE" >> /home/user/sdr/multirx2/post.log

for a in $(/home/user/mdc-decode/mdc_decoder $NEWFILE | cut -d' ' -f4 | sort -u)
do
    mkdir -p ${SAVE_DIR}/units/$a
    ln -s $2 ${SAVE_DIR}/units/$a
    echo "$(date) $a $2" >> /home/user/sdr/multirx2/post.log
done
