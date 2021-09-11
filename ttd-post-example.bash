#!/bin/bash
export TZ=EST5EDT

PAGEDIR=/var/www/html/wav/pager/

sleep 2
/home/user/wave2ttd.py $1 | while read A
do
	mkdir -p ${PAGEDIR}${A}
	NEWFILE=${PAGEDIR}${A}/$(date +%Y-%m-%d_)$(basename $1 .wav).mp3
	/usr/bin/lame --silent $1 ${NEWFILE}
	echo "$(date) $A $NEWFILE" >> /home/user/sdr/multirx2/pages.log

	echo ${NEWFILE} >> /home/user/call_list
	tail -20 /home/user/call_list > /home/user/new_call_list
	rm /home/user/call_list
	mv /home/user/new_call_list /home/user/call_list

#	if [[ $A =~ .*FIRE.* ]]; then
#		/home/user/send-audio-email.py -f xyz@example.com -s "$A Alert" -r 9085551212@vzwpix.com  ${NEWFILE}
#	fi
	if [[ $A =~ 21_RESCUE ]]; then
		/home/user/send-audio-email.py -f xyz@example.com -s "$A Alert" -r sammy@example.com  ${NEWFILE}
	fi
	if [[ $A =~ 21_FIRE ]]; then
		/home/user/send-audio-email.py -f xyz@example.com -s "$A Alert" -r freddy@example.com  ${NEWFILE}
	fi
	if [[ $A =~ 22_HAZMAT ]]; then
		/home/user/push_call.bash ${DIR}${FILE} 19085551212
	fi
done

rm $1
