#!/bin/bash
# Will be executed as user "root".


echo "<INFO> Installing raspiBackup"
echo "<INFO> Current Dir is"
pwd



# Install raspiBackup
chmod +x ./raspiBackupInstall.sh
bash ./raspiBackupInstall.sh -c > REPLACELBPLOGDIR/raspiBackup.log 2>&1
chmod a+w REPLACELBPLOGDIR/raspiBackup.log

# We have to default raspiBackup to not zip, as we cannot override this for rsync backups (will fail)
#	sed -i.bak 's/^\(DEFAULT_ZIP_BACKUP=\).*/\1"0"/' $lbbackupconfig 

# Create backup directory if missing
if [ ! -d "/backup" ]; then
	mkdir -p /backup
	chown loxberry:loxberry /backup 
fi

exit 0
