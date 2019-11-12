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
use LoxBerry::Web;
use LoxBerry::Log;
use LoxBerry::Storage;
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
my  $version = "1.0.4.1";
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

$pcfg->autosave(1);

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

$pcfg->param("JITBACKUP.DESTINATION", "/backup") if (! $pcfg->param("JITBACKUP.DESTINATION"));

$pcfg->param("DDZ.DESTINATION", "/backup") if (! $pcfg->param("DDZ.DESTINATION"));  
$pcfg->param("RSYNC.DESTINATION", "/backup") if (! $pcfg->param("RSYNC.DESTINATION")); 
$pcfg->param("TGZ.DESTINATION", "/backup") if (! $pcfg->param("TGZ.DESTINATION"));

$pcfg->param("DDZ.RETENTION", "3") if (! $pcfg->param("DDZ.RETENTION"));
$pcfg->param("RSYNC.RETENTION", "3") if (! $pcfg->param("RSYNC.RETENTION"));
$pcfg->param("TGZ.RETENTION", "3") if (! $pcfg->param("TGZ.RETENTION"));

$pcfg->param("JITBACKUP.TYPE", "DDZ") if (! $pcfg->param("JITBACKUP.TYPE"));

my $p = $pcfg->vars();

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
# Initialize html templates
##########################################################################

# Navigation Bar

$navbar{1}{Name} = "LoxBerry Backup";
$navbar{1}{URL} = 'index.cgi';
$navbar{1}{Notify_Package} = $lbpplugindir;
# $navbar{1}{Notify_NAme} = 'daemon';
 
$navbar{2}{Name} = $L{'COMMON.LOGFILES'};
$navbar{2}{URL} = "?form=logfiles";
$navbar{2}{Notify_Package} = $lbpplugindir;
 

##########################################################################
# Process form data
##########################################################################

if ($R::form eq 'logfiles') {
	logfiles();
}

if ($R::jit_backup) {
	# Data were posted - save 
	&jit_backup;
}

$p = $pcfg->vars();

##########################################################################
# Create some variables for the Template
##########################################################################

$navbar{1}{active} = 1;
$maintemplate->param('mainform', 1);

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

my $jit_path = LoxBerry::Storage::get_storage_html(
	formid => 'jit_destination',
	currentpath => $pcfg->param("JITBACKUP.DESTINATION"),
	custom_folder => 1,
	readwriteonly => 1,
	label => $L{'BACKUP.LABEL_JIT_DESTINATION'},
	type_usb => 1,
	type_net => 1,
	type_custom => 1,
	show_browse => 1,
);
$maintemplate->param( 'DROPDOWN_JIT_DESTINATION' => $jit_path );



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
			$val{'SCHEDULE_CLOCK'} = sprintf("%02d:%02d", $event->hour(), $event->minute());
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
	
	
	$val{'DROPDOWN_DESTINATION'} = LoxBerry::Storage::get_storage_html(
		formid => $type . 'cron_destination',
		currentpath => $val{"DESTINATION"},
		custom_folder => 1,
		readwriteonly => 1,
		label => $L{'BACKUP.LABEL_DESTINATION'},
		type_usb => 1,
		type_net => 1,
		type_custom => 1,
		data_mini => 1,
		show_browse => 1,
	);
	
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
								  -checked => is_enabled($p->{'CONFIG.EMAIL_NOTIFICATION'}),
									-value => 1,
									-label => $L{'BACKUP.OPTION_TRADITIONAL_EMAIL'},
								);
$maintemplate->param( EMAIL_NOTIFICATION => $email_notification_html);

my $fake_backup_html = checkbox(-name => 'fake_backup',
  -checked => is_enabled($p->{'CONFIG.FAKE_BACKUP'}),
	-value => 1,
	-label => $L{'BACKUP.OPTION_FAKE_BACKUP'},
);
$maintemplate->param( 'FAKE_BACKUP' => $fake_backup_html);
									
my @stop_services_array = $pcfg->param("CONFIG.STOPSERVICES");
if (@stop_services_array) {
	$stop_services = join( "\r\n", @stop_services_array);
}  
$maintemplate->param( STOP_SERVICES => $stop_services);
						
$maintemplate->param( CHECKPIDURL => "./grep_raspibackup.cgi");

printTemplate();

##########################################################################
# AJAX routines
##########################################################################
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
			-command => "$lbpbindir/runbackup.pl type=$R::key scheduled=true > /dev/null 2>&1",
			-user => 'loxberry',
			-system => 1,
		);
		
		# Decide timeplan
		if ($R::timebase eq "days") {
			my ($runhour, $runmin) = split(/:/, $R::clock);
			my $datetime;
			if($runhour && $runmin && $runhour >= 0 && $runhour <= 24 && $runmin >= 0 && $runmin <= 59) {
				$datetime = "$runmin " . "$runhour " . "*/$R::period " . "* " . "*";
			} else {	
				$datetime = "0 " . "4 " . "*/$R::period " . "* " . "*";
			}
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
			%L = LoxBerry::System::readlanguage(undef, "language.ini");
			print $L{'BACKUP.HINT_DEST_DOES_NOT_EXIST'};
		}
	}
	
	if ($R::action eq "runbackup") {
		system("$lbpbindir/runbackup.pl > /dev/null 2>&1 &");
		my $exitcode = $? >> 8;
		if ($exitcode != 0) {
			print $cgi->header(-status => "500 Error starting backup");
		} else {
			print $cgi->header(-status => "204 Backup successfully started");
		}
	}

	exit;
}

sub installcrontab
{
	if (! -e $crontabtmp) {
		return (0);
	}
	qx ( $lbhomedir/sbin/installcrontab.sh $lbpplugindir $crontabtmp );
	if ($!) {
		print $cgi->header(-status => "500 Error activating new crontab");
		return(0);
	}
	return(1);
}

sub logfiles
{
	$navbar{2}{active} = 1;
	
	$maintemplate->param('logfilesform', 1);
	
	my $loglist = LoxBerry::Web::loglist_html();
	$maintemplate->param('logfilelist_html', $loglist);
	
	printTemplate();

}


##########################################################################
# Print Template
##########################################################################
sub printTemplate
{						

	# Header
	LoxBerry::Web::lbheader("LoxBerry Backup", "http://www.loxwiki.eu:80/x/14U_AQ");
	print LoxBerry::Log::get_notifications_html($lbpplugindir);
	print $maintemplate->output;

	LoxBerry::Web::lbfooter();

	exit;
}