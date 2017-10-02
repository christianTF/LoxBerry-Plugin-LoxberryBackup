# LoxBerry-Plugin-LoxberryBackup
Backup Plugin für den LoxBerry

This plugin is a LoxBerry webinterface for raspiBackup (https://www.linux-tips-and-tricks.de/de/schnellstart-rbk).

What it should do:
- The code should get a system plugin for LoxBerry >=0.3, therefore should be included in the default LoxBerry image.
- For LoxBerry 0.2.x it should be a normal plugin
- It should support only two types of backups (raspiBackup will do lot more):
  - DDZ (zipped DD image) that can be restored with Win32Diskimager (big & slow but easy to restore)
  - rsync to locally attached disks/sticks or mounted ext3/ext4 partitions (quick, but more effort to restore)
- It should support raspiBackup's email notification  
- It should support the user to choose the backup destination
- It should support the user to restore from an rsync backup

What it NOT should do:
- Mounting network devices
