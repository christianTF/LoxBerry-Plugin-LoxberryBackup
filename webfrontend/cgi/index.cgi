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
use FindBin;
use lib "$FindBin::Bin/./perllib";
use LoxBerry::System;
use LoxBerry::Web;

use Switch;
use CGI::Carp qw(fatalsToBrowser);
use CGI qw/:standard/;
use Config::Simple;
# String::Escape needs to be installed!
# use String::Escape qw( unquotemeta );
use HTML::Template;
use warnings;
use strict;
no strict "refs"; # we need it for template system and for contructs like ${"skalar".$i} in loops

# For debug purposes
use Data::Dumper;


##########################################################################
# Variables
##########################################################################
our  $cgi = CGI->new;
my  $pcfg;
my  $lang;
my  $languagefile;
my  $version;
my  $pname;
my  $languagefileplugin;
my  %TPhrases;
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

my $dd_backup_command;
my $tgz_backup_command;
my $rsync_backup_command;

our @backuptypes = ('DD', 'RSYNC', 'TGZ');

##########################################################################
# Read Settings
##########################################################################

# Version of this script
$version = "0.11";
 my $datestring = localtime();
 print STDERR "========== LoxBerry Backup Version $version === ($datestring) =========\n";
 print STDERR "Global variables from LoxBerry::System\n";
 print STDERR "Homedir:     $lbhomedir\n";
 print STDERR "Plugindir:   $lbplugindir\n";
 print STDERR "CGIdir:      $lbcgidir\n";
 print STDERR "HTMLdir:     $lbhtmldir\n";
 print STDERR "Templatedir: $lbtemplatedir\n";
 print STDERR "Datadir:     $lbdatadir\n";
 print STDERR "Logdir:      $lblogdir\n";
 print STDERR "Configdir:   $lbconfigdir\n";

# Start with HTML header
print $cgi->header(
         -type    =>      'text/html',
         -charset =>      'utf-8'
);

# Get language from GET, POST or System setting (from LoxBerry::Web)
$lang = lblanguage();

##########################################################################
# Read and process config
##########################################################################

# Read plugin config 
$pcfg 	= new Config::Simple("$lbconfigdir/lbbackup.cfg");
if (! defined $pcfg) {
	$pcfg = new Config::Simple(syntax=>'ini');
	$pcfg->param("CONFIG.VERSION", $version);
	$pcfg->write("$lbconfigdir/lbbackup.cfg");
	$pcfg = new Config::Simple("$lbconfigdir/lbbackup.cfg");
}
# Set default parameters

my $ddcron = defined $pcfg->param("DD.SCHEDULE") ? $pcfg->param("DD.SCHEDULE") : "off";
my $rsynccron = defined $pcfg->param("RSYNC.SCHEDULE") ? $pcfg->param("RSYNC.SCHEDULE") : "off";
my $tgzcron = defined $pcfg->param("TGZ.SCHEDULE") ? $pcfg->param("TGZ.SCHEDULE") : "off";

my $ddcron_retention = defined $pcfg->param("DD.RETENTION") ? $pcfg->param("DD.RETENTION") : "3";
my $rsynccron_retention = defined $pcfg->param("RSYNC.RETENTION") ? $pcfg->param("RSYNC.RETENTION") : "3";
my $tgzcron_retention = defined $pcfg->param("TGZ.RETENTION") ? $pcfg->param("TGZ.RETENTION") : "3";

my @stop_services_array = $pcfg->param("CONFIG.STOPSERVICES");
if (@stop_services_array) {
	$stop_services = join( "\r\n", @stop_services_array);
}  

my $email_notification = $pcfg->param("CONFIG.EMAIL_NOTIFICATION") ne "" ? $pcfg->param("CONFIG.EMAIL_NOTIFICATION") : "0";
my $fake_backup = is_enabled($pcfg->param("CONFIG.FAKE_BACKUP"));

# $pcfg->write();


##########################################################################
# Process form data
##########################################################################

if ($cgi->param("save")) {
	# Data were posted - save 
	&save;
}

if ($cgi->param("jit_backup")) {
	# Data were posted - save 
	&jit_backup;
}

#our $postdata = $cgi->param('ddcron');
print STDERR "POSTDATA:";
print STDERR Dumper($cgi);
#print STDERR $postdata;


##########################################################################
# Initialize html templates
##########################################################################

# See http://www.perlmonks.org/?node_id=65642


# Topmenu
$topmenutemplate = HTML::Template->new(
	filename => "$lbtemplatedir/multi/topmenu.html",
	global_vars => 1,
	loop_context_vars => 1,
	die_on_bad_params => 0,
);

# Main
#$maintemplate = HTML::Template->new(filename => "$lbtemplatedir/multi/main.html");
$maintemplate = HTML::Template->new(
	filename => "$lbtemplatedir/multi/backup.html",
	global_vars => 1,
	loop_context_vars => 1,
	die_on_bad_params => 0,
	associate => $pcfg,
);

# Activate Backup button in topmenu
$topmenutemplate->param( CLASS_INDEX => 'class="ui-btn-active ui-state-persist"');


# Footer # At the moment not in HTML::Template format
# $footertemplate = HTML::Template->new(
	# filename => "$lbhomedir/templates/system/$lang/footer.html",
	# die_on_bad_params => 0,
	# associate => $cgi,
# );



##########################################################################
# Translations
##########################################################################

# Init Language
# Clean up lang variable
$lang         =~ tr/a-z//cd;
$lang         = substr($lang,0,2);

# Read Plugin transations
# Read English language as default
# Missing phrases in foreign language will fall back to English
$languagefileplugin 	= "$lbtemplatedir/en/language.txt";
Config::Simple->import_from($languagefileplugin, \%TPhrases);

# Read foreign language if exists and not English
$languagefileplugin = "$lbtemplatedir/$lang/language.txt";
# Now overwrite phrase variables with user language
if ((-e $languagefileplugin) and ($lang ne 'en')) {
	Config::Simple->import_from($languagefileplugin, \%TPhrases);
}

# Parse phrase variables to html templates
while (my ($name, $value) = each %TPhrases){
	$maintemplate->param("T::$name" => $value);
	#$headertemplate->param("T::$name" => $value);
	#$footertemplate->param("T::$name" => $value);
}

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

my $dd_radio_group = radio_group(
						-name => 'ddcron',
						-values => ['off', 'daily', 'weekly', 'monthly', 'yearly'],
						-labels => \%labels,
						-default => $ddcron ,
						);
$maintemplate->param( DD_RADIO_GROUP => $dd_radio_group);

my $rsync_radio_group = radio_group(
						-name => 'rsynccron',
						-values => ['off', 'daily', 'weekly', 'monthly', 'yearly'],
						-labels => \%labels,
						-default => $rsynccron ,
						);
$maintemplate->param( RSYNC_RADIO_GROUP => $rsync_radio_group);

my $tgz_radio_group = radio_group(
						-name => 'tgzcron',
						-values => ['off', 'daily', 'weekly', 'monthly', 'yearly'],
						-labels => \%labels,
						-default => $tgzcron ,
						);
$maintemplate->param( TGZ_RADIO_GROUP => $tgz_radio_group);

my $email_notification_html = checkbox(-name => 'email_notification',
								  -checked => $email_notification,
									-value => 1,
									-label => 'E-Mail Benachrichtigung',
								);
$maintemplate->param( EMAIL_NOTIFICATION => $email_notification_html);

my $fake_backup_html = checkbox(-name => 'fake_backup',
  -checked => $fake_backup,
	-value => 1,
	-label => 'FAKE Backup',
);
$maintemplate->param( FAKE_BACKUP => $fake_backup_html);
									
$maintemplate->param( STOP_SERVICES => $stop_services);
						
$maintemplate->param( CHECKPIDURL => "./grep_raspibackup.cgi");
						
##########################################################################
# Print Template
##########################################################################

# Header
#print $headertemplate->output;

# In LoxBerry V0.2.x we use the old LoxBerry::Web header
LoxBerry::Web::lbheader("LoxBerry Backup", "http://www.loxwiki.eu:80/x/14U_AQ");

# Topmenu
print $topmenutemplate->output;

# Main
print $maintemplate->output;

# Footer
#print $footertemplate->output;

# In LoxBerry V0.2.x we use the old LoxBerry::Web footer
LoxBerry::Web::lbfooter();

exit;

##########################################################################
# Save data
##########################################################################
sub save 
{
	$ddcron = $cgi->param('ddcron');
	$rsynccron = $cgi->param('rsynccron');
	$tgzcron = $cgi->param('tgzcron');
	
	$ddcron_retention = $cgi->param('ddcron_retention');
	$rsynccron_retention = $cgi->param('rsynccron_retention');
	$tgzcron_retention = $cgi->param('tgzcron_retention');
	
	$email_notification = defined $cgi->param('email_notification') ? "1" : "0";
	
	$stop_services = $cgi->param('stop_services');
	
	$fake_backup = defined $cgi->param('fake_backup') ? "1" : "0";
	
	# Write schedules to config if it appears in the possible schedule list
	my @schedules = qw ( off daily weekly monthly yearly );
		
	if ( $ddcron ~~ @schedules ) {
		$pcfg->param("DD.SCHEDULE", $ddcron);
	} else {
		$ddcron = "off";
		$pcfg->param("DD.SCHEDULE", $ddcron);
	}
	
	if ( $rsynccron ~~ @schedules ) {
		$pcfg->param("RSYNC.SCHEDULE", $rsynccron);
	} else {
		$rsynccron = "off";
		$pcfg->param("RSYNC.SCHEDULE", $rsynccron);
	}
	if ( $tgzcron ~~ @schedules ) {
		$pcfg->param("TGZ.SCHEDULE", $tgzcron);
	} else {
		$tgzcron = "off";
		$pcfg->param("TGZ.SCHEDULE", $tgzcron);
	}
	
	# Write retentions if it is a number
	if ( $ddcron_retention =~ /^[0-9,.]+$/ ) {
		$pcfg->param("DD.RETENTION", $ddcron_retention);
	} else {
		$ddcron_retention = 3;
		$pcfg->param("DD.RETENTION", $ddcron_retention);
	}
	if ( $rsynccron_retention =~ /^[0-9,.]+$/ ) {
		$pcfg->param("RSYNC.RETENTION", $rsynccron_retention);
	} else {
		$rsynccron_retention = 3;
		$pcfg->param("RSYNC.RETENTION", $rsynccron_retention);
	}
	if ( $tgzcron_retention =~ /^[0-9,.]+$/ ) {
		$pcfg->param("TGZ.RETENTION", $tgzcron_retention);
	} else {
		$tgzcron_retention = 3;
		$pcfg->param("TGZ.RETENTION", $tgzcron_retention);
	}
	
	$pcfg->param("CONFIG.EMAIL_NOTIFICATION", $email_notification);
	$pcfg->param("CONFIG.FAKE_BACKUP", $fake_backup);
	
	
	# Stop services
	print STDERR "\nSTOP SERVICES\n";
	my $stop_services_list = $stop_services;
	$stop_services_list =~ s/(\r?\n)+/,/g;
	$pcfg->param("CONFIG.STOPSERVICES", $stop_services_list);
		
	$pcfg->write();

	# Unlink all cron jobs
	
	foreach my $currtype (@backuptypes) {
		print STDERR "Deleting cronjobs for ${lbplugindir}_$currtype\n";
		unlink ("$lbhomedir/system/cron/cron.daily/${lbplugindir}_$currtype");
		unlink ("$lbhomedir/system/cron/cron.weekly/${lbplugindir}_$currtype");
		unlink ("$lbhomedir/system/cron/cron.monthly/${lbplugindir}_$currtype");
		unlink ("$lbhomedir/system/cron/cron.yearly/${lbplugindir}_$currtype");
	}
	
	### Create new cronjobs
	# Create start/stop options for services
	my @stop_services_array = $pcfg->param("CONFIG.STOPSERVICES");
	# Remove empty elements
	@stop_services_array = grep /\S/, @stop_services_array;
	
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
	
	$mail_params = email_params();
	
	get_raspibackup_command();

	if ($ddcron ne "off") {
		my $filename = "$lbhomedir/system/cron/cron.$ddcron/${lbplugindir}_DD";
		unless(open FILE, '>'.$filename) {
			$errormsg = "Cron job for DD backup - Cannot create file $filename";
			print STDERR "$errormsg\n";
		}
		print FILE "#!/bin/bash\n";
		print FILE "cd $lblogdir\n";
		print FILE $dd_backup_command;
		close FILE;
		chmod 0775, $filename;
	}
		
	if ($tgzcron ne "off") {
		my $filename = "$lbhomedir/system/cron/cron.$tgzcron/${lbplugindir}_TGZ";
		unless(open FILE, '>'.$filename) {
			$errormsg = "Cron job for TGZ backup - Cannot create file $filename";
			print STDERR "$errormsg\n";
		}
		print FILE "#!/bin/bash\n";
		print FILE "cd $lblogdir\n";
		print FILE $tgz_backup_command;
		close FILE;
		chmod 0775, $filename;
	}
	
	if ($rsynccron ne "off") {
		my $filename = "$lbhomedir/system/cron/cron.$rsynccron/${lbplugindir}_RSYNC";
		unless(open FILE, '>'.$filename) {
			$errormsg = "Cron job for RSYNC backup - Cannot create file $filename";
			print STDERR "$errormsg\n";
		}
		print FILE "#!/bin/bash\n";
		print FILE "cd $lblogdir\n";
		print FILE $rsync_backup_command;
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
	
	my $backuptype = $cgi->param('jit-backup-type');
	
	## Email notification
	my $email_notification = defined $pcfg->param('email_notification') ? "1" : "0";
	my $email_params = email_params();

	## Create start/stop options for services
	my @stop_services_array = $pcfg->param("CONFIG.STOPSERVICES");
	# Remove empty elements
	@stop_services_array = grep /\S/, @stop_services_array;
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
	$jit_retention = $ddcron_retention > $rsynccron_retention ? $ddcron_retention : $rsynccron_retention;
	$jit_retention = $jit_retention > $tgzcron_retention ? $jit_retention : $tgzcron_retention;
	print STDERR "JIT Retention number (max) was identified as $jit_retention.\n";

	get_raspibackup_command();
	
	my $filename = "$lbdatadir/jit_backup";
	unless(open FILE, '>'.$filename) {
		$errormsg = "Cron job for $backuptype backup - Cannot create file $filename";
		print STDERR "$errormsg\n";
	}
	print FILE "#!/bin/bash\n";
	print FILE "cd $lblogdir\n";
	if ($backuptype eq "DD") { print FILE $dd_backup_command; }
	elsif ($backuptype eq "TGZ") { print FILE $tgz_backup_command; }
	elsif ($backuptype eq "RSYNC") { print FILE $rsync_backup_command; }
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
	
	print STDERR "Checking E-Mail notification...";
	if ($email_notification eq "1") {
			print STDERR "Mail Notification is enabled.\n";
			my $mailcfg = new Config::Simple("$lbhomedir/config/system/mail.cfg");
			unless($mailadr = $mailcfg->param("SMTP.EMAIL"))
			{ 		
			print STDERR "Error reading mail configuration in $lbhomedir/config/system/mail.cfg\n";
			$mailadr = undef;
			}
			print STDERR ($mailadr ne "" ? "Mail Address is $mailadr\n" : "Mail notification disabled\n");
	}
	$mail_params = $mailadr ne "" ? "-e $mailadr " : "";
	return $mail_params;
}


# -----------------------------------------------------------
# Generate raspiBackup commandline
# -----------------------------------------------------------
sub get_raspibackup_command
{
    my $fake_backup_params;
	if (is_enabled($fake_backup)) { 
		print STDERR "FAKE Backup is enabled.\n";
		$fake_backup_params = "-F ";
	}
	# DD
	$dd_backup_command = 
		"sudo raspiBackup.sh " .
		$fake_backup_params . 
		"-o \"$par_stopservices\" " .
		"-a \"$par_startservices\" " .
		$mail_params .
		"-k $ddcron_retention " .
		"-t ddz " .
		"-L current " .
		"/backup\n";
	print STDERR "DD backup command: " . $dd_backup_command;
		
	# TGZ
	$tgz_backup_command = 
		"sudo raspiBackup.sh " .
		$fake_backup_params . 
		"-o \"$par_stopservices\" " .
		"-a \"$par_startservices\" " .
		$mail_params .
		"-k $tgzcron_retention " .
		"-t tgz " .
		"-L current " .
		"/backup\n";
	print STDERR "TGZ backup command: " . $tgz_backup_command;
	
	# rsync
	$rsync_backup_command = 
		"sudo raspiBackup.sh " .
		$fake_backup_params . 
		"-o \"$par_stopservices\" " .
		"-a \"$par_startservices\" " .
		$mail_params .
		"-k $rsynccron_retention " .
		"-t rsync " .
		"-L current " .
		"/backup\n";
	print STDERR "RSYNC backup command: " . $rsync_backup_command;
	



}
