#!/bin/bash
# Will be executed as user "root".

loxberryhome=$5
pluginname=$3
lbbackupconfig="/usr/local/etc/raspiBackup.conf"

echo "<INFO> Installing raspiBackup"

# Install raspiBackup
chmod +x /tmp/uploads/$1/bin/raspiBackupInstall.sh
bash /tmp/uploads/$1/bin/raspiBackupInstall.sh -c > /tmp/uploads/$1/log/raspiBackup.log 2>&1
chmod a+w /tmp/uploads/$1/log/raspiBackup.log

# We have to default raspiBackup to not zip, as we cannot override this for rsync backups (will fail)
#	sed -i.bak 's/^\(DEFAULT_ZIP_BACKUP=\).*/\1"0"/' $lbbackupconfig 

# Create backup directory if missing
if [ ! -d "/backup" ]; then
	mkdir -p /backup
	chown loxberry:loxberry /backup 
fi

exit 0
