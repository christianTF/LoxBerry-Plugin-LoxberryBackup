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
my $maintemplate;
my $footertemplate;

my $dd_schedule;
my $dd_retention;
my $rsync_schedule;
my $rsync_retention;
my $tgz_schedule;
my $tgz_retention;
my $stop_services;

##########################################################################
# Read Settings
##########################################################################

# Version of this script
$version = "0.11";

# print STDERR "Global variables from LoxBerry::System\n";
# print STDERR "Homedir:     $lbhomedir\n";
# print STDERR "Plugindir:   $lbplugindir\n";
# print STDERR "CGIdir:      $lbcgidir\n";
# print STDERR "HTMLdir:     $lbhtmldir\n";
# print STDERR "Templatedir: $lbtemplatedir\n";
# print STDERR "Datadir:     $lbdatadir\n";
# print STDERR "Logdir:      $lblogdir\n";
# print STDERR "Configdir:   $lbconfigdir\n";

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
if (defined @stop_services_array) {
	$stop_services = join( "\r\n", @stop_services_array);
}  

# $pcfg->write();


##########################################################################
# Process form data
##########################################################################

if ($cgi->param gt 0) {
	# Data were posted - save 
	&save;
}


our $postdata = $cgi->param('ddcron');
print STDERR "POSTDATA:";
print STDERR Dumper($cgi);
print STDERR $postdata;





##########################################################################
# Initialize html templates
##########################################################################

# See http://www.perlmonks.org/?node_id=65642

# Header # At the moment not in HTML::Template format
#$headertemplate = HTML::Template->new(
#	filename => "$lbhomedir/templates/system/$lang/header.html",
#	die_on_bad_params => 0,
#	associate => $cgi,
#);

# Main
#$maintemplate = HTML::Template->new(filename => "$lbtemplatedir/multi/main.html");
$maintemplate = HTML::Template->new(
	filename => "$lbtemplatedir/multi/backup.html",
	global_vars => 1,
	loop_context_vars => 1,
	die_on_bad_params => 0,
	associate => $pcfg,
);


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
# As an example: we create a select list for a form in two different ways
###

# First create a select list for a from - data is taken from the Plugin 
# Config file. We are using the HTML::Template Loop function. You should
# be familiar with Hashes and Arrays in Perl.
#
# Please see https://metacpan.org/pod/HTML::Template
# Please see http://www.perlmonks.org/?node_id=65642
#
# This is the prefered way, because code and style is seperated. But
# it is a little bit complicated. If you could not understand this,
# please see next example.

# Create an array with the sections we would like to read. These
# Sections exist in the plugin config file.
# See https://wiki.selfhtml.org/wiki/Perl/Listen_bzw._Arrays
my @sections = ("DDCRON","TGZCRON");

# Now we put the options from the 3 sections into a (new) hash (we check if
# they exist at first). This newly created hash will be referenced in an array.
# Perl only allows referenced hashes in arrays, so we are not allowed to
# overwrite the single hashes!
# my $i = 0;
# my @array;
# foreach (@sections) {
        # #if ( $plugin_cfg->param("$_.NAME") ) {
                # %{"hash".$i} = ( # Create a new hash each time, e.g. %hash1, %hash2 etc.
                # OPTION_NAME	=>	%TPhrases{$_}{Name},
                # ID		=>	$plugin_cfg->param("$_.ID"),
                # );
                # push (@array, \%{"hash".$i}); 	# Attach a reference to the newly created
						# # hash to the array
                # $i++;
		# #}	
# }
# Let the Loop with name "SECTIONS" be available in the template
# $maintemplate->param( SECTIONS => \@array );

# This was complicated? Yes, it is because you have to understand hashes and arrays in Perl.
# We can do the very same if we mix code and style here. It's not as "clean", but it is
# easier to understand.

# Again we read the options from the 3 sections from our config file. But we now will create
# the select list for the form right here - not as before in the template.
# my $selectlist;
# foreach (@sections) {
        # if ( $plugin_cfg->param("$_.NAME") ) {
		# # This appends a new option line to $selectlist
		# $selectlist .= "<option value='".$plugin_cfg->param("$_.ID")."'>".$plugin_cfg->param("$_.NAME")."</option>\n";
	# }
# }
# Let the Var $selectlist with the name SELECTLIST be available in the template
# $maintemplate->param( SELECTLIST => $selectlist );

###
# As an example: we create some vars for the template
###
$maintemplate->param( PLUGINNAME => $pname );
$maintemplate->param( ANOTHERNAME => "This is another Name" );

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

$maintemplate->param( STOP_SERVICES => $stop_services);
						

##########################################################################
# Print Template
##########################################################################

# Header
#print $headertemplate->output;

# In LoxBerry V0.2.x we use the old LoxBerry::Web header
LoxBerry::Web::lbheader("Sample Plugin V2", "https://www.loxforum.com/forum/projektforen/loxberry/entwickler/84645-best-practise-perl-programmierung-im-loxberry");

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
	
	$stop_services = $cgi->param('stop_services');
	
	# Write schedules to config if it appears in the possible schedule list
	my @schedules = qw ( off daily weekly monthly yearly );
		
	if ( $ddcron ~~ @schedules ) {
		$pcfg->param("DD.SCHEDULE", $ddcron);
	} 
	if ( $rsynccron ~~ @schedules ) {
		$pcfg->param("RSYNC.SCHEDULE", $rsynccron);
	}
	if ( $tgzcron ~~ @schedules ) {
		$pcfg->param("TGZ.SCHEDULE", $tgzcron);
	}
	
	# Write retentions if it is a number
	if ( $ddcron_retention =~ /^[0-9,.]+$/ ) {
		$pcfg->param("DD.RETENTION", $ddcron_retention);
	}
	if ( $rsynccron_retention =~ /^[0-9,.]+$/ ) {
		$pcfg->param("RSYNC.RETENTION", $rsynccron_retention);
	}
	if ( $tgzcron_retention =~ /^[0-9,.]+$/ ) {
		$pcfg->param("TGZ.RETENTION", $tgzcron_retention);
	}
	
	# Stop services
	print STDERR "\nSTOP SERVICES\n";
	my $stop_services_list = $stop_services;
	$stop_services_list =~ s/(\r?\n)+/,/g;
		
	print STDERR "Stop services: $stop_services\n";
	$pcfg->param("CONFIG.STOPSERVICES", $stop_services_list);
		
	$pcfg->write();
	
}


