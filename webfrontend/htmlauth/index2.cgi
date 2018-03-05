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
use Config::Crontab;

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

my $crontabtmp = "$lbplogdir/crontab.temp";
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
my $pluginversion;

my $dd_backup_command;
my $tgz_backup_command;
my $rsync_backup_command;

my @backuptypes = ( "DDZ", "TGZ", "RSYNC");

$cgi->import_names('R');



##########################################################################
# Read and process config
##########################################################################

# Read plugin config 
$pcfg 	= new Config::Simple("$lbpconfigdir/lbbackup.cfg");

if (! defined $pcfg) {
	$pluginversion = LoxBerry::System::pluginversion();
	$pcfg = new Config::Simple(syntax=>'ini');
	$pcfg->param("CONFIG.VERSION", $pluginversion);
	$pcfg->write("$lbpconfigdir/lbbackup.cfg");
	$pcfg = new Config::Simple("$lbpconfigdir/lbbackup.cfg");
}

##########################################################################
# Read crontab
##########################################################################

my $crontab = new Config::Crontab;
$crontab->system(1); ## Wichtig, damit der User im File berücksichtigt wird
$crontab->read( -file => "$lbhomedir/system/cron/cron.d/$lbpplugindir" );

print STDERR "Crontab:\n";

# foreach my $type (@backuptypes) {
	# my ($comment) = $crontab->select( -type => 'comment', -data => '## Backuptype ' . $type );
	# print STDERR "Comment found\n" if ($comment);
	# my ($block) = $crontab->block($comment) if ($comment);
	# print STDERR "Block found\n" if ($block);
	# my ($event) = $block->select ( -type => 'event' ) if ($block);
	# print STDERR "Event: " . $event->command() . "\n" if ($event);
# }


# Handle AJAX requests
if ($R::action) { 
	ajax();
}

##########################################################################
# Read Settings
##########################################################################
if (! $pluginversion) {
	$pluginversion = LoxBerry::System::pluginversion();
}
my $datestring = localtime();
print STDERR "========== LoxBerry Backup Version $pluginversion === ($datestring) =========\n";

# Set default parameters

# $pcfg->param("CONFIG.JITDESTINATION", "/backup") if (! $pcfg->param("CONFIG.JITDESTINATION"));

$pcfg->param("DD.DESTINATION", "/backup") if (! $pcfg->param("DD.DESTINATION"));  
$pcfg->param("RSYNC.DESTINATION", "/backup") if (! $pcfg->param("RSYNC.DESTINATION")); 
$pcfg->param("TGZ.DESTINATION", "/backup") if (! $pcfg->param("TGZ.DESTINATION"));

$pcfg->param("DD.RETENTION", "3") if (! $pcfg->param("DD.RETENTION"));
$pcfg->param("RSYNC.RETENTION", "3") if (! $pcfg->param("RSYNC.RETENTION"));
$pcfg->param("TGZ.RETENTION", "3") if (! $pcfg->param("TGZ.RETENTION"));

$pcfg->param("JITBACKUP.TYPE", "DDZ") if (! $pcfg->param("JITBACKUP.TYPE"));

# $pcfg->param("CONFIG.EMAIL_NOTIFICATION", "0") if (is_disabled($pcfg->param("CONFIG.EMAIL_NOTIFICATION")));
# $pcfg->param("CONFIG.FAKE_BACKUP", "0") if (! is_disabled($pcfg->param("CONFIG.FAKE_BACKUP"))); 


my $p = $pcfg->vars();




##########################################################################
# Template and language settings
##########################################################################

# Main
$maintemplate = HTML::Template->new(
	filename => "$lbptemplatedir/backup2.html",
	global_vars => 1,
	loop_context_vars => 1,
	die_on_bad_params => 0,
	associate => $pcfg,
);

%L = LoxBerry::System::readlanguage($maintemplate, "language.ini");


##########################################################################
# Process form data
##########################################################################

if ($R::jit_backup) {
	# Data were posted - save 
	&jit_backup;
}

$p = $pcfg->vars();

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


my %jittypelabels;
foreach my $type (@backuptypes) {
	$jittypelabels{$type} = $L{ $type . ".JITSELECT" };
}

my $jittype=  radio_group(-name=>'jitbackuptype',
			     -values => \@backuptypes,
			     -default => $p->{'JITBACKUP.TYPE'},
			     #-linebreak=>'true',
				-labels=>\%jittypelabels,
         #  -attributes=>\%attributes
	);
$maintemplate->param( 'JITTYPE' => $jittype );


my @backupselection;
foreach my $type (@backuptypes) {
	my %val;
	my $bc = $pcfg->param(-block => $type);
		
	
	$val{'TYPE'} = $type;
	$val{'LABEL'} = $L{ $type . ".LABEL" };
	$val{'DESTINATION'} = $bc->{DESTINATION};
	$val{'RETENTION'} = $bc->{RETENTION};
	
	#$val{'SCHEDULE_TIME'} = $bc->{SCHEDULE_TIME};
	
	my ($comment) = $crontab->select( -type => 'comment', -data => '## Backuptype ' . $type );
	# print STDERR "Comment found\n" if ($comment);
	my ($block) = $crontab->block($comment) if ($comment);
	# print STDERR "Block found\n" if ($block);
	my ($event) = $block->select ( -type => 'event' ) if ($block);
	#print STDERR "Event: " . $event->command() . "\n" if ($event);
	if ($event) {
		my @tmp_days = split(/\//, $event->dom(), 2);
		my @tmp_hours = split(/\//, $event->hour(), 2);
		if ($tmp_days[1]) {
			$val{'SCHEDULE_TIME'} = $tmp_days[1];
			$val{'SELECTED_DAYS'} = "selected";
		} elsif ($tmp_hours[1]) {
			$val{'SCHEDULE_TIME'} = $tmp_hours[1];
			$val{'SELECTED_HOURS'} = "selected";
		} else {
			$val{'SCHEDULE_TIME'} = "0";
			$val{'SELECTED_DISABLED'} = "selected";
		}
		#print STDERR "$type Event: " . $event->hour . " hr / " . $event->dom()  . " day\n";
	
	
	
	}
	
	
	
	
	# $val{'SCHEDULE_TIMEBASE'} = 
	push @backupselection, \%val;

}
$maintemplate->param ( 'BACKUPSELECTION', \@backupselection);

if (is_enabled($p->{"CONFIG.NOTIFY_BACKUP_INFOS"})) {
	$maintemplate->param("NOTIFY_BACKUP_INFOS", 'checked="checked"');
} else {
	$maintemplate->param("NOTIFY_BACKUP_INFOS", '');
}

if (is_enabled($p->{"CONFIG.NOTIFY_BACKUP_ERRORS"})) {
	$maintemplate->param("NOTIFY_BACKUP_ERRORS", 'checked="checked"');
} else {
	$maintemplate->param("NOTIFY_BACKUP_ERRORS", '');
}

my $email_notification_html = checkbox(-name => 'email_notification',
								  -checked => $p->{'CONFIG.EMAIL_NOTIFICATION'},
									-value => 1,
									-label => 'E-Mail Benachrichtigung',
								);
$maintemplate->param( EMAIL_NOTIFICATION => $email_notification_html);

my $fake_backup_html = checkbox(-name => 'fake_backup',
  -checked => $p->{'CONFIG.FAKE_BACKUP'},
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

# ##########################################################################
# # Save data
# ##########################################################################
# sub save 
# {
	
	# my $notify_infos = is_enabled($R::NOTIFY_BACKUP_INFOS) ? "on" : "off";
	# my $notify_errors = is_enabled($R::NOTIFY_BACKUP_ERRORS) ? "on" : "off";
	
	# my $email_notification = $R::email_notification ? "1" : "0";
	# my $fake_backup = $R::fake_backup ? "1" : "0";
	
	# print STDERR "Notify_infos: $notify_infos / Notify_errors: $notify_errors\n";
	
	# # Write schedules to config if it appears in the possible schedule list
	# my @schedules = qw ( off daily weekly monthly yearly );

	# if ( $R::ddcron ~~ @schedules ) {
		# $pcfg->param("DD.SCHEDULE", $R::ddcron);
	# } else {
		# $pcfg->param("DD.SCHEDULE", "off");
	# }
	
	# if ( $R::rsynccron ~~ @schedules ) {
		# $pcfg->param("RSYNC.SCHEDULE", $R::rsynccron);
	# } else {
		# $pcfg->param("RSYNC.SCHEDULE", "off");
	# }
	# if ( $R::tgzcron ~~ @schedules ) {
		# $pcfg->param("TGZ.SCHEDULE", $R::tgzcron);
	# } else {
		# $pcfg->param("TGZ.SCHEDULE", "off");
	# }
	
	# $pcfg->param("DD.DESTINATION", $R::ddcron_destination);
	# $pcfg->param("RSYNC.DESTINATION", $R::rsynccron_destination);
	# $pcfg->param("TGZ.DESTINATION", $R::tgzcron_destination);
	
	# $pcfg->param("DD.RETENTION", $R::ddcron_retention);
	# $pcfg->param("RSYNC.RETENTION", $R::rsynccron_retention);
	# $pcfg->param("TGZ.RETENTION", $R::tgzcron_retention);

	# $pcfg->param("CONFIG.NOTIFY_BACKUP_INFOS", $notify_infos);
	# $pcfg->param("CONFIG.NOTIFY_BACKUP_ERRORS", $notify_errors);
	
	# $pcfg->param("CONFIG.EMAIL_NOTIFICATION", $email_notification);
	# $pcfg->param("CONFIG.FAKE_BACKUP", $fake_backup);
		
	# # Stop services
	# my $stop_services_list = $R::stop_services;
	# $stop_services_list =~ s/\r//g;
	# my @stop_services_array = split(/\n/, $stop_services_list);
	# # Remove empty elements
	# @stop_services_array = grep /\S/, @stop_services_array;
	# print STDERR "STOP SERVICES ARRAY: @stop_services_array\n";
	
	# $pcfg->param("CONFIG.STOPSERVICES" , \@stop_services_array);
		
	# $pcfg->write();
	
	# # Unlink all cron jobs
	
	# foreach my $currtype (@backuptypes) {
		# print STDERR "Deleting cronjobs for ${lbpplugindir}_$currtype\n";
		# unlink ("$lbhomedir/system/cron/cron.daily/${lbpplugindir}_$currtype");
		# unlink ("$lbhomedir/system/cron/cron.weekly/${lbpplugindir}_$currtype");
		# unlink ("$lbhomedir/system/cron/cron.monthly/${lbpplugindir}_$currtype");
		# unlink ("$lbhomedir/system/cron/cron.yearly/${lbpplugindir}_$currtype");
	# }
	
	# ### Create new cronjobs
	
	# foreach my $service (@stop_services_array) {
		# $service = trim($service);
		# if ($service ne "") {
			# $par_stopservices .= "service $service stop && ";
			# $par_startservices .= "service $service start && ";
		# }
	# }
	# # Remove trailing &&'s, or write : if empty
	# $par_stopservices = $par_stopservices ne "" ? substr ($par_stopservices, 0, -3) : ":";
	# $par_startservices = $par_startservices ne "" ? substr ($par_startservices, 0, -3) : ":";
	
	# $mail_params = email_params();

	# my $notifyscript = qq(
# if [ "\$?" = "0" ]; then
	# notify_ext PACKAGE=$lbpplugindir NAME=backup MESSAGE="LoxBerry Backup: The last scheduled backup has successfully finished." SEVERITY=6 LOGFILE=plugins/$lbpplugindir/raspiBackup.log
# else
	# notify_ext PACKAGE=lbupdate NAME=backup MESSAGE="LoxBerry Backup: ERROR creating the last scheduled backup. See the logfile for more information." SEVERITY=3 LOGFILE=plugins/$lbpplugindir/raspiBackup.log
# fi
# );

	# get_raspibackup_command();

	# if ($R::ddcron ne "off") {
		# my $filename = "$lbhomedir/system/cron/cron." . $R::ddcron . "/${lbpplugindir}_DD";
		# unless(open FILE, '>'.$filename) {
			# $errormsg = "Cron job for DD backup - Cannot create file $filename";
			# print STDERR "$errormsg\n";
		# }
		# print FILE "#!/bin/bash\n";
		# print FILE ". $lbhomedir/libs/bashlib/notify.sh\n";
		# print FILE "cd $lbplogdir\n";
		# print FILE $dd_backup_command;
		# print FILE $notifyscript;
		# close FILE;
		# chmod 0775, $filename;
	# }
		
	# if ($R::tgzcron ne "off") {
		# my $filename = "$lbhomedir/system/cron/cron." . $R::tgzcron . "/${lbpplugindir}_TGZ";
		# unless(open FILE, '>'.$filename) {
			# $errormsg = "Cron job for TGZ backup - Cannot create file $filename";
			# print STDERR "$errormsg\n";
		# }
		# print FILE "#!/bin/bash\n";
		# print FILE ". $lbhomedir/libs/bashlib/notify.sh\n";
		# print FILE "cd $lbplogdir\n";
		# print FILE $tgz_backup_command;
		# print FILE $notifyscript;
		# close FILE;
		# chmod 0775, $filename;
	# }
	
	# if ($R::rsynccron ne "off") {
		# my $filename = "$lbhomedir/system/cron/cron." . $R::rsynccron . "/${lbpplugindir}_RSYNC";
		# unless(open FILE, '>'.$filename) {
			# $errormsg = "Cron job for RSYNC backup - Cannot create file $filename";
			# print STDERR "$errormsg\n";
		# }
		# print FILE "#!/bin/bash\n";
		# print FILE ". $lbhomedir/libs/bashlib/notify.sh\n";
		# print FILE "cd $lbplogdir\n";
		# print FILE $rsync_backup_command;
		# print FILE $notifyscript;
		# close FILE;
		# chmod 0775, $filename;
	# }
	
# }

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
	notify_ext PACKAGE=$lbpplugindir NAME=backup _ISPLUGIN=1 MESSAGE="LoxBerry Backup: The last scheduled backup has successfully finished." SEVERITY=6 LOGFILE=$lbplogdir/raspiBackup.log
else
	notify_ext PACKAGE=lbupdate NAME=backup _ISPLUGIN=1 MESSAGE="LoxBerry Backup: ERROR creating the last scheduled backup. See the logfile for more information." SEVERITY=3 LOGFILE=$lbplogdir/raspiBackup.log
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

sub ajax
{

	if ($R::action eq "changecron" && $R::key && $R::timebase) 
		{
		
		if (-e $crontabtmp) {
			unlink $crontabtmp;
		}
		
		my ($comment) = $crontab->select( -type => 'comment', -data => '## Backuptype ' . $R::key );
		
		# Schedule does not exist and should be removed --> nothing to do
		if (! $comment && is_disabled($R::timebase)) {
			print $cgi->header(-status => "204 Schedule does not exist - Nothing to do");
			exit(0);
		}
		
		# We fully remove the old block
		if ($comment) {
			my ($block) = $crontab->block($comment);
			$crontab->remove($block);
		}
		
		if (is_disabled($R::timebase) || ! $R::period || $R::period < 1) {
			# We are finished, write the crontab
			$crontab->write($crontabtmp);
			if (installcrontab()) {
				print $cgi->header(-status => "204 Removed $R::key backup from cron");
			}
			exit(0);
		}
		
		# Disabling processing done. Now changing time plan
		
		# Create the event
		my $event = new Config::Crontab::Event (
			-command => "/opt/loxberry/bin/plugins/lbbackup/runbackup.pl type=$R::key scheduled=true",
			-user => 'loxberry',
			-system => 1,
		);
		
		# Decide timeplan
		if ($R::timebase eq "days") {
			my $datetime = "0 " . "4 " . "*/$R::period " . "* " . "*";
			$event->datetime($datetime);
		} elsif ($R::timebase eq "hours") {
			my $datetime = "0 " . "*/$R::period " . "* " . "* " . "*";
			$event->datetime($datetime);
		} else {
			print $cgi->header(-status => "500 timebase $R::timebase not supported");
			exit(0);
		}
		
		# Insert block and event to crontab
		
		my $block = new Config::Crontab::Block;
		$block->last( new Config::Crontab::Comment( -data => '## Backuptype ' . $R::key ) );
		$block->last($event);
		$crontab->last($block);
		
		$crontab->write($crontabtmp);
		if (installcrontab()) {
			print $cgi->header(-status => "204 Written new crontab");
		}

		# # Schedule was changed
		# eval {
			# $pcfg->param($R::key . ".PERIOD", $R::period);
			# $pcfg->param($R::key . ".TIMEBASE", $R::timebase);
			# $pcfg->write;
		# };
		# if ($@) {
			# print $cgi->header(-status => "500 Error writing plugin config");
		# }
			
		# print $cgi->header(-status => "204 OK");
		exit;
	}
	if ($R::action eq "changeconfig" && $R::key) 
	{
		my @tmp_key = split(/\./, $R::key);
				
		
		eval {
			if (! $R::value) {
				$pcfg->delete(trim($R::key));
			} else {
				$pcfg->param(trim($R::key), trim($R::value));
			}
			$pcfg->write;
		};
		if ($@) {
			print $cgi->header(-status => "500 Error writing plugin config");
			exit(1);
		}
		print $cgi->header(-status => "200 Written to plugin config");
		
		print STDERR "tmp_key1: $tmp_key[1] \n";
		print STDERR "value: $R::value \n";
		
		
		if ($tmp_key[1] && $tmp_key[1] eq "DESTINATION" && ! -d $R::value) {
			print "Directory does not exist (but value was saved).";
		}
	}
	exit;

}

sub installcrontab
{
	if (! -e $crontabtmp) {
		return (0);
	}
	qx ( sudo $lbhomedir/sbin/installcrontab.sh $lbpplugindir $crontabtmp );
	if ($!) {
		print $cgi->header(-status => "500 Error activating new crontab");
		return(0);
	}
	return(1);
}