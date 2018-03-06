#!/bin/bash

# Bashscript which is executed by bash *AFTER* complete installation is done
# (but *BEFORE* postupdate). Use with caution and remember, that all systems
# may be different! Better to do this in your own Pluginscript if possible.
#
# Exit code must be 0 if executed successfull.
#
# Will be executed as user "loxberry".
#
# We add 5 arguments when executing the script:
# command <TEMPFOLDER> <NAME> <FOLDER> <VERSION> <BASEFOLDER>
#
# For logging, print to STDOUT. You can use the following tags for showing
# different colorized information during plugin installation:
#
# <OK> This was ok!"
# <INFO> This is just for your information."
# <WARNING> This is a warning!"
# <ERROR> This is an error!"
# <FAIL> This is a fail!"

# To use important variables from command line use the following code:
ARGV0=$0 # Zero argument is shell command
ARGV1=$1 # First argument is temp folder during install
ARGV2=$2 # Second argument is Plugin-Name for scipts etc.
ARGV3=$3 # Third argument is Plugin installation folder
ARGV4=$4 # Forth argument is Plugin version
ARGV5=$5 # Fifth argument is Base folder of LoxBerry

if [ ! -e REPLACELBPLOGDIR ]; then
	echo "<INFO> Creating log directory REPLACELBPLOGDIR"
	mkdir -p REPLACELBPLOGDIR
fi

rm $LBHOMEDIR/system/cron/cron.daily/$2* >/dev/null
if [ $? -eq 0 ]; then
	echo "<WARNING> Deleting old daily schedules" 
	UPGRADE=1
fi

rm -f $LBHOMEDIR/system/cron/cron.weekly/$2*
if [ $? -eq 0 ]; then
	echo "<WARNING> Deleting old weekly schedules"
	UPGRADE=1
fi

rm -f $LBHOMEDIR/system/cron/cron.monthly/$2*
if [ $? -eq 0 ]; then
	echo "<WARNING> Deleting old monthly schedules"
	UPGRADE=1
fi

rm -f $LBHOMEDIR/system/cron/cron.yearly/$2*
if [ $? -eq 0 ]; then
	echo "<WARNING> Deleting old yearly schedules ($LBHOMEDIR/system/cron/cron.yearly/$2*) "
	UPGRADE=1
fi

if [ -n "$UPGRADE" ]; then
	. $LBHOMEDIR/libs/bashlib/notify.sh
	notify $3 Update "LoxBerry Backup changed the schedule system. Please reconfigure the schedules of your backups. No more automatic backups will be done otherwise." err
	echo "<WARNING> LoxBerry Backup changed the schedule system. Please reconfigure the schedules of your backups. No more automatic backups will be done otherwise."
	fi

# Exit with Status 0
exit 0
