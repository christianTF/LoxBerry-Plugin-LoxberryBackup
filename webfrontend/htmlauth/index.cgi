#!/usr/bin/perl

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


##########################################################################
# Modules
##########################################################################
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;

use CGI qw/:standard/;
# String::Escape needs to be installed!
# use String::Escape qw( unquotemeta );
use warnings;
use strict;

# For debug purposes
# use Data::Dumper;


##########################################################################
# Variables
##########################################################################
our  $cgi = CGI->new;
my  $pcfg;
my  $lang;
my  $languagefile;
my  $version = "1.0.1_1";
my  $pname;
my  $languagefileplugin;
my $topmenutemplate;
my $maintemplate;
my $footertemplate;

my $dd_schedule;
my $dd_retention;
my $rsync_schedule;
my $rsync_retention;
my $tgz_schedule;
my $tgz_retention;
my $stop_services;
my $par_stopservices;
my $par_startservices;
my $mail_params;
our $errormsg;
our %navbar;

my $dd_backup_command;
my $tgz_backup_command;
my $rsync_backup_command;

our @backuptypes = ('DD', 'RSYNC', 'TGZ');

##########################################################################
# Read Settings
##########################################################################

 my $pluginversion = LoxBerry::System::pluginversion();
 my $datestring = localtime();
 print STDERR "========== LoxBerry Backup Version $pluginversion === ($datestring) =========\n";
 # print STDERR "Global variables from LoxBerry::System\n";
 # print STDERR "Homedir:     $lbhomedir\n";
 # print STDERR "Plugindir:   $lbpplugindir\n";
 # print STDERR "CGIdir:      $lbphtmlauthdir\n";
 # print STDERR "HTMLdir:     $lbphtmldir\n";
 # print STDERR "Templatedir: $lbptemplatedir\n";
 # print STDERR "Datadir:     $lbpdatadir\n";
 # print STDERR "Logdir:      $lbplogdir\n";
 # print STDERR "Configdir:   $lbpconfigdir\n";

$cgi->import_names('R');

##########################################################################
# Read and process config
##########################################################################

# Read plugin config 
$pcfg 	= new Config::Simple("$lbpconfigdir/lbbackup.cfg");

if (! defined $pcfg) {
	$pcfg = new Config::Simple(syntax=>'ini');
	$pcfg->param("CONFIG.VERSION", $pluginversion);
	$pcfg->write("$lbpconfigdir/lbbackup.cfg");
	$pcfg = new Config::Simple("$lbpconfigdir/lbbackup.cfg");
}

# Set default parameters

# $pcfg->param("CONFIG.JITDESTINATION", "/backup") if (! $pcfg->param("CONFIG.JITDESTINATION"));

$pcfg->param("DD.SCHEDULE", "off") if (! $pcfg->param("DD.SCHEDULE"));
$pcfg->param("RSYNC.SCHEDULE", "off") if (! $pcfg->param("RSYNC.SCHEDULE"));
$pcfg->param("TGZ.SCHEDULE", "off") if (! $pcfg->param("TGZ.SCHEDULE"));

$pcfg->param("DD.DESTINATION", "/backup") if (! $pcfg->param("DD.DESTINATION"));  
$pcfg->param("RSYNC.DESTINATION", "/backup") if (! $pcfg->param("RSYNC.DESTINATION")); 
$pcfg->param("TGZ.DESTINATION", "/backup") if (! $pcfg->param("TGZ.DESTINATION"));

$pcfg->param("DD.RETENTION", "3") if (! $pcfg->param("DD.RETENTION"));
$pcfg->param("RSYNC.RETENTION", "3") if (! $pcfg->param("RSYNC.RETENTION"));
$pcfg->param("TGZ.RETENTION", "3") if (! $pcfg->param("TGZ.RETENTION"));

# $pcfg->param("CONFIG.EMAIL_NOTIFICATION", "0") if (is_disabled($pcfg->param("CONFIG.EMAIL_NOTIFICATION")));
# $pcfg->param("CONFIG.FAKE_BACKUP", "0") if (! is_disabled($pcfg->param("CONFIG.FAKE_BACKUP"))); 


my $C = $pcfg->vars();

##########################################################################
# Template and language settings
##########################################################################

# Main
$maintemplate = HTML::Template->new(
	filename => "$lbptemplatedir/backup.html",
	global_vars => 1,
	loop_context_vars => 1,
	die_on_bad_params => 0,
	associate => $pcfg,
);

%L = LoxBerry::System::readlanguage($maintemplate, "language.ini");


##########################################################################
# Process form data
##########################################################################

if ($R::save) {
	# Data were posted - save 
	&save;
}

if ($R::jit_backup) {
	# Data were posted - save 
	&jit_backup;
}

$C = $pcfg->vars();

#our $postdata = $cgi->param('ddcron');
print STDERR "POSTDATA:";
# print STDERR Dumper($cgi);
# print STDERR $postdata;


##########################################################################
# Initialize html templates
##########################################################################

# Navigation Bar

$navbar{1}{Name} = "LoxBerry Backup";
$navbar{1}{URL} = 'index.cgi';
$navbar{1}{Notify_Package} = $lbpplugindir;
# $navbar{1}{Notify_NAme} = 'daemon';
 
$navbar{2}{Name} = "Logfile";
$navbar{2}{URL} = "/admin/system/tools/logfile.cgi?logfile=plugins/$lbpplugindir/raspiBackup.log&header=html&format=template";
$navbar{2}{target} = "_blank";
# $navbar{1}{Notify_Package} = $lbpplugindir;
# $navbar{1}{Notify_NAme} = 'cronjob';
 
$navbar{1}{active} = 1;

##########################################################################
# Create some variables for the Template
##########################################################################

###
# As an example: we create some vars for the template
###
$maintemplate->param( PLUGINNAME => 'LoxBerry Backup' );

my %labels = ( 
	'off' => 'Aus',
	'daily' => 'Taeglich',
	'weekly' => 'Woechentlich',
	'monthly' => 'Monatlich',
	'yearly' => 'Jaehrlich',
);

#my %label_attributes = ('off'=>{'class'=>'

my $dd_radio_group = radio_group(
						-name => 'ddcron',
						-values => ['off', 'daily', 'weekly', 'monthly', 'yearly'],
						-labels => \%labels,
						-default => $C->{'DD.SCHEDULE'} ,
						);
$maintemplate->param( DD_RADIO_GROUP => $dd_radio_group);

my $rsync_radio_group = radio_group(
						-name => 'rsynccron',
						-values => ['off', 'daily', 'weekly', 'monthly', 'yearly'],
						-labels => \%labels,
						-default => $C->{'RSYNC.SCHEDULE'} ,
						);
$maintemplate->param( RSYNC_RADIO_GROUP => $rsync_radio_group);

my $tgz_radio_group = radio_group(
						-name => 'tgzcron',
						-values => ['off', 'daily', 'weekly', 'monthly', 'yearly'],
						-labels => \%labels,
						-default => $C->{'TGZ.SCHEDULE'} ,
						);
						
$maintemplate->param( TGZ_RADIO_GROUP => $tgz_radio_group);

if (is_enabled($C->{"CONFIG.NOTIFY_BACKUP_INFOS"})) {
	$maintemplate->param("NOTIFY_BACKUP_INFOS", 'checked="checked"');
} else {
	$maintemplate->param("NOTIFY_BACKUP_INFOS", '');
}

if (is_enabled($C->{"CONFIG.NOTIFY_BACKUP_ERRORS"})) {
	$maintemplate->param("NOTIFY_BACKUP_ERRORS", 'checked="checked"');
} else {
	$maintemplate->param("NOTIFY_BACKUP_ERRORS", '');
}

my $email_notification_html = checkbox(-name => 'email_notification',
								  -checked => $C->{'CONFIG.EMAIL_NOTIFICATION'},
									-value => 1,
									-label => 'E-Mail Benachrichtigung',
								);
$maintemplate->param( EMAIL_NOTIFICATION => $email_notification_html);

my $fake_backup_html = checkbox(-name => 'fake_backup',
  -checked => $C->{'CONFIG.FAKE_BACKUP'},
	-value => 1,
	-label => 'FAKE Backup',
);
$maintemplate->param( FAKE_BACKUP => $fake_backup_html);
									
my @stop_services_array = $pcfg->param("CONFIG.STOPSERVICES");
if (@stop_services_array) {
	$stop_services = join( "\r\n", @stop_services_array);
}  
$maintemplate->param( STOP_SERVICES => $stop_services);
						
$maintemplate->param( CHECKPIDURL => "./grep_raspibackup.cgi");
						
##########################################################################
# Print Template
##########################################################################

# Header
LoxBerry::Web::lbheader("LoxBerry Backup", "http://www.loxwiki.eu:80/x/14U_AQ");
print LoxBerry::Log::get_notifications_html($lbpplugindir);
print $maintemplate->output;

LoxBerry::Web::lbfooter();

exit;

##########################################################################
# Save data
##########################################################################
sub save 
{
	
	my $notify_infos = is_enabled($R::NOTIFY_BACKUP_INFOS) ? "on" : "off";
	my $notify_errors = is_enabled($R::NOTIFY_BACKUP_ERRORS) ? "on" : "off";
	
	my $email_notification = $R::email_notification ? "1" : "0";
	my $fake_backup = $R::fake_backup ? "1" : "0";
	
	print STDERR "Notify_infos: $notify_infos / Notify_errors: $notify_errors\n";
	
	# Write schedules to config if it appears in the possible schedule list
	my @schedules = qw ( off daily weekly monthly yearly );

	if ( $R::ddcron ~~ @schedules ) {
		$pcfg->param("DD.SCHEDULE", $R::ddcron);
	} else {
		$pcfg->param("DD.SCHEDULE", "off");
	}
	
	if ( $R::rsynccron ~~ @schedules ) {
		$pcfg->param("RSYNC.SCHEDULE", $R::rsynccron);
	} else {
		$pcfg->param("RSYNC.SCHEDULE", "off");
	}
	if ( $R::tgzcron ~~ @schedules ) {
		$pcfg->param("TGZ.SCHEDULE", $R::tgzcron);
	} else {
		$pcfg->param("TGZ.SCHEDULE", "off");
	}
	
	$pcfg->param("DD.DESTINATION", $R::ddcron_destination);
	$pcfg->param("RSYNC.DESTINATION", $R::rsynccron_destination);
	$pcfg->param("TGZ.DESTINATION", $R::tgzcron_destination);
	
	$pcfg->param("DD.RETENTION", $R::ddcron_retention);
	$pcfg->param("RSYNC.RETENTION", $R::rsynccron_retention);
	$pcfg->param("TGZ.RETENTION", $R::tgzcron_retention);

	$pcfg->param("CONFIG.NOTIFY_BACKUP_INFOS", $notify_infos);
	$pcfg->param("CONFIG.NOTIFY_BACKUP_ERRORS", $notify_errors);
	
	$pcfg->param("CONFIG.EMAIL_NOTIFICATION", $email_notification);
	$pcfg->param("CONFIG.FAKE_BACKUP", $fake_backup);
		
	# Stop services
	my $stop_services_list = $R::stop_services;
	$stop_services_list =~ s/\r//g;
	my @stop_services_array = split(/\n/, $stop_services_list);
	# Remove empty elements
	@stop_services_array = grep /\S/, @stop_services_array;
	print STDERR "STOP SERVICES ARRAY: @stop_services_array\n";
	
	$pcfg->param("CONFIG.STOPSERVICES" , \@stop_services_array);
		
	$pcfg->write();
	
	# Unlink all cron jobs
	
	foreach my $currtype (@backuptypes) {
		print STDERR "Deleting cronjobs for ${lbpplugindir}_$currtype\n";
		unlink ("$lbhomedir/system/cron/cron.daily/${lbpplugindir}_$currtype");
		unlink ("$lbhomedir/system/cron/cron.weekly/${lbpplugindir}_$currtype");
		unlink ("$lbhomedir/system/cron/cron.monthly/${lbpplugindir}_$currtype");
		unlink ("$lbhomedir/system/cron/cron.yearly/${lbpplugindir}_$currtype");
	}
	
	### Create new cronjobs
	
	foreach my $service (@stop_services_array) {
		$service = trim($service);
		if ($service ne "") {
			$par_stopservices .= "service $service stop && ";
			$par_startservices .= "service $service start && ";
		}
	}
	# Remove trailing &&'s, or write : if empty
	$par_stopservices = $par_stopservices ne "" ? substr ($par_stopservices, 0, -3) : ":";
	$par_startservices = $par_startservices ne "" ? substr ($par_startservices, 0, -3) : ":";
	
	$mail_params = email_params();

	my $notifyscript = qq(
if [ "\$?" = "0" ]; then
	notify_ext PACKAGE=$lbpplugindir NAME=backup MESSAGE="LoxBerry Backup: The last scheduled backup has successfully finished." SEVERITY=6 LOGFILE=plugins/$lbpplugindir/raspiBackup.log
else
	notify_ext PACKAGE=lbupdate NAME=backup MESSAGE="LoxBerry Backup: ERROR creating the last scheduled backup. See the logfile for more information." SEVERITY=3 LOGFILE=plugins/$lbpplugindir/raspiBackup.log
fi
);

	get_raspibackup_command();

	if ($R::ddcron ne "off") {
		my $filename = "$lbhomedir/system/cron/cron." . $R::ddcron . "/${lbpplugindir}_DD";
		unless(open FILE, '>'.$filename) {
			$errormsg = "Cron job for DD backup - Cannot create file $filename";
			print STDERR "$errormsg\n";
		}
		print FILE "#!/bin/bash\n";
		print FILE ". $lbhomedir/libs/bashlib/notify.sh\n";
		print FILE "cd $lbplogdir\n";
		print FILE $dd_backup_command;
		print FILE $notifyscript;
		close FILE;
		chmod 0775, $filename;
	}
		
	if ($R::tgzcron ne "off") {
		my $filename = "$lbhomedir/system/cron/cron." . $R::tgzcron . "/${lbpplugindir}_TGZ";
		unless(open FILE, '>'.$filename) {
			$errormsg = "Cron job for TGZ backup - Cannot create file $filename";
			print STDERR "$errormsg\n";
		}
		print FILE "#!/bin/bash\n";
		print FILE ". $lbhomedir/libs/bashlib/notify.sh\n";
		print FILE "cd $lbplogdir\n";
		print FILE $tgz_backup_command;
		print FILE $notifyscript;
		close FILE;
		chmod 0775, $filename;
	}
	
	if ($R::rsynccron ne "off") {
		my $filename = "$lbhomedir/system/cron/cron." . $R::rsynccron . "/${lbpplugindir}_RSYNC";
		unless(open FILE, '>'.$filename) {
			$errormsg = "Cron job for RSYNC backup - Cannot create file $filename";
			print STDERR "$errormsg\n";
		}
		print FILE "#!/bin/bash\n";
		print FILE ". $lbhomedir/libs/bashlib/notify.sh\n";
		print FILE "cd $lbplogdir\n";
		print FILE $rsync_backup_command;
		print FILE $notifyscript;
		close FILE;
		chmod 0775, $filename;
	}
	
}
##########################################################################
# Just-In-Time Backup
##########################################################################
sub jit_backup
{
	my $datestring = localtime();
	print STDERR "==== JIT-Backup started! == ($datestring) ==\n";
	
	$pcfg->param('CONFIG.JITDESTINATION', $R::jit_destination);
	$pcfg->write();
	
	
	my $backuptype = $cgi->param("jit-backup-type");
	
	## Email notification
	my $email_notification = defined $pcfg->param('email_notification') ? "1" : "0";
	my $email_params = email_params();

	## Create start/stop options for services
	my $stop_services_list = $R::stop_services;
	$stop_services_list =~ s/\r//g;
	my @stop_services_array = split(/\n/, $stop_services_list);
	# Remove empty elements
	@stop_services_array = grep /\S/, @stop_services_array;
	
	undef $par_stopservices;
	undef $par_startservices;
	
	foreach my $service (@stop_services_array) {
		$service = trim($service);
		if ($service ne "") {
			$par_stopservices .= "service $service stop &&";
			$par_startservices .= "service $service start &&";
		}
	}
	# Remove trailing &&'s, or write : if empty
	$par_stopservices = $par_stopservices ne "" ? substr ($par_stopservices, 0, -3) : ":";
	$par_startservices = $par_startservices ne "" ? substr ($par_startservices, 0, -3) : ":";

	## Get the highest retention number
	my $jit_retention;
	$jit_retention = 10;
	print STDERR "JIT Retention number (max) was identified as $jit_retention.\n";

	my $notifyscript = qq(
if [ "\$?" = "0" ]; then
	notify_ext PACKAGE=$lbpplugindir NAME=backup MESSAGE="LoxBerry Backup: The last scheduled backup has successfully finished." SEVERITY=6 LOGFILE=plugins/$lbpplugindir/raspiBackup.log
else
	notify_ext PACKAGE=lbupdate NAME=backup MESSAGE="LoxBerry Backup: ERROR creating the last scheduled backup. See the logfile for more information." SEVERITY=3 LOGFILE=plugins/$lbpplugindir/raspiBackup.log
fi
);

	get_raspibackup_command($R::jit_destination, $jit_retention);
	
	my $filename = "$lbpdatadir/jit_backup";
	unless(open FILE, '>'.$filename) {
		$errormsg = "JIT backup job for $backuptype backup - Cannot create file $filename";
		print STDERR "$errormsg\n";
	}
	print FILE "#!/bin/bash\n";
	print FILE ". $lbhomedir/libs/bashlib/notify.sh\n";
	print FILE "cd $lbplogdir\n";
	if ($backuptype eq "DD") { print FILE $dd_backup_command; }
	elsif ($backuptype eq "TGZ") { print FILE $tgz_backup_command; }
	elsif ($backuptype eq "RSYNC") { print FILE $rsync_backup_command; }
	print FILE "$notifyscript";
	close FILE;
	chmod 0775, $filename;
	
	my $pid = fork();
	die "Fork failed: $!" if !defined $pid;
	if ($pid == 0) {
			 # do this in the child
			 print STDERR "---> Backup process forked.\n";
			 open STDIN, "</dev/null";
			 open STDOUT, ">/dev/null";
			 open STDERR, ">/dev/null";
			 if (system("$filename &") == 0) {
			 print STDERR "---> Backup command started.";
			 } else {
			 print STDERR "---> Backup command returned ERROR.";
			 };
	}
	return;
}

# -----------------------------------------------------------
# Generate E-Mail Options
# -----------------------------------------------------------
sub email_params
{
	my $mailadr = "";
	my $mail_params = "";
	my $friendlyname;
	
	print STDERR "Checking E-Mail notification...";
	if ($R::email_notification eq "1") {
			$friendlyname = trim(lbfriendlyname() . " LoxBerry");
			
			print STDERR "Mail Notification is enabled.\n";
			my $mailcfg = new Config::Simple("$lbsconfigdir/mail.cfg");
			unless($mailadr = $mailcfg->param("SMTP.EMAIL"))
			{ 		
			print STDERR "Error reading mail configuration in $lbsconfigdir/mail.cfg\n";
			$mailadr = undef;
			}
			print STDERR ($mailadr ne "" ? "Mail Address is $mailadr\n" : "Mail notification disabled\n");
	}
	$mail_params = $mailadr ne "" ? "-e $mailadr -E \"-r $mailadr\" " : "";
	return $mail_params;
}


# -----------------------------------------------------------
# Generate raspiBackup commandline
# -----------------------------------------------------------
sub get_raspibackup_command
{
    my ($destparam, $jit_retention) = @_;
	my $dest;
	$destparam = trim($destparam);
	
	my $fake_backup_params;
		
	if (is_enabled($R::fake_backup)) { 
		print STDERR "FAKE Backup is enabled.\n";
		$fake_backup_params = "-F ";
	}
	# DD
	$dest = $destparam ? $destparam : trim($R::ddcron_destination);
	$dd_backup_command = 
		"sudo raspiBackup.sh " .
		$fake_backup_params . 
		"-N \"fstab disk temp\" " . 
		"-o \"$par_stopservices\" " .
		"-a \"$par_startservices\" " .
		$mail_params .
		"-k " . ($jit_retention ? $jit_retention : $R::ddcron_retention) . " " .
		"-t ddz " .
#		"-z+ " .
		"-L current " .
		"$dest\n";
	print STDERR "DD backup command: " . $dd_backup_command;
		
	# TGZ
	$dest = $destparam ? $destparam : trim($R::tgzcron_destination);
	$tgz_backup_command = 
		"sudo raspiBackup.sh " .
		$fake_backup_params . 
		"-N \"fstab disk temp\" " . 
		"-o \"$par_stopservices\" " .
		"-a \"$par_startservices\" " .
		$mail_params .
		"-k " . ($jit_retention ? $jit_retention : $R::tgzcron_retention) . " " .
		"-t tgz " .
#		"-z+ " .
		"-L current " .
		"$dest\n";
	print STDERR "TGZ backup command: " . $tgz_backup_command;
	
	# rsync
	$dest = $destparam ? $destparam : trim($R::rsynccron_destination);
	$rsync_backup_command = 
		"sudo raspiBackup.sh " .
		$fake_backup_params . 
		"-N \"fstab disk temp\" " . 
		"-o \"$par_stopservices\" " .
		"-a \"$par_startservices\" " .
		$mail_params .
		"-k " . ($jit_retention ? $jit_retention : $R::rsynccron_retention) . " " .
		"-t rsync " .
#		"-z- " .
		"-L current " .
		"$dest\n";
	print STDERR "RSYNC backup command: " . $rsync_backup_command;

}
