#!/bin/bash
# Will be executed as user "root".

echo "<INFO> Installing raspiBackup"

# Copy raspiBackup Config
cp -f $5/data/plugins/$3/raspiBackup.conf /usr/local/etc/

# Copy raspiBackup


chmod +x $5/data/plugins/$3/raspiBackup*.sh
mv -f $5/data/plugins/$3/raspiBackup.sh /usr/local/bin/
mv -f $5/data/plugins/$3/raspiBackup_*.sh /usr/local/bin/

echo "<INFO>Framp's raspiBackup version installed:"
bash /usr/local/bin/raspiBackup.sh --version

# We have to default raspiBackup to not zip, as we cannot override this for rsync backups (will fail)
#	sed -i.bak 's/^\(DEFAULT_ZIP_BACKUP=\).*/\1"0"/' $lbbackupconfig 

# Create backup directory if missing
if [ ! -d "/backup" ]; then
	echo "<INFO> Creating default /backup directory"
	mkdir -p /backup
	chown loxberry:loxberry /backup 
fi

if [ -e "$LBHOMEDIR/system/cron/cron.d/$2" ]; then
	chown root:root $LBHOMEDIR/system/cron/cron.d/$2
fi

exit 0
