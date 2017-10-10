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

use CGI::Carp qw(fatalsToBrowser);
use CGI qw/:standard/;
use Config::Simple;
# String::Escape needs to be installed!
# use String::Escape qw( unquotemeta );
use HTML::Template;
use warnings;
use strict;
no strict "refs"; # we need it for template system and for contructs like ${"skalar".$i} in loops

##########################################################################
# Variables
##########################################################################
my  $cgi = new CGI;
my  $plugin_cfg;
my  $lang;
my  $languagefile;
my  $version;
my  $pname;
my  $languagefileplugin;
my  %TPhrases;
my  $maintemplate;

##########################################################################
# Read Settings
##########################################################################

# Version of this script
$version = "0.11";

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
        type    =>      'text/html',
        charset =>      'utf-8',
);

# Get language from GET, POST or System setting (from LoxBerry::Web)
$lang = lblanguage();

# Read plugin config
$plugin_cfg 	= new Config::Simple("$lbconfigdir/lbbackup.cfg");
# $pname          = $plugin_cfg->param("MAIN.SCRIPTNAME");

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
	filename => "$lbtemplatedir/multi/main.html",
	global_vars => 1,
	loop_context_vars => 1,
	die_on_bad_params => 0,
	associate => $cgi,
);


# Footer # At the moment not in HTML::Template format
#$footertemplate = HTML::Template->new(
#	filename => "$lbhomedir/templates/system/$lang/footer.html",
#	die_on_bad_params => 0,
#	associate => $cgi,
#);



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
my @sections = ("SECTION1","SECTION2","SECTION3");

# Now we put the options from the 3 sections into a (new) hash (we check if
# they exist at first). This newly created hash will be referenced in an array.
# Perl only allows referenced hashes in arrays, so we are not allowed to
# overwrite the single hashes!
my $i = 0;
my @array;
foreach (@sections) {
        if ( $plugin_cfg->param("$_.NAME") ) {
                %{"hash".$i} = ( # Create a new hash each time, e.g. %hash1, %hash2 etc.
                OPTION_NAME	=>	$plugin_cfg->param("$_.NAME"),
                ID		=>	$plugin_cfg->param("$_.ID"),
                );
                push (@array, \%{"hash".$i}); 	# Attach a reference to the newly created
						# hash to the array
                $i++;
	}	
}
# Let the Loop with name "SECTIONS" be available in the template
$maintemplate->param( SECTIONS => \@array );

# This was complicated? Yes, it is because you have to understand hashes and arrays in Perl.
# We can do the very same if we mix code and style here. It's not as "clean", but it is
# easier to understand.

# Again we read the options from the 3 sections from our config file. But we now will create
# the select list for the form right here - not as before in the template.
my $selectlist;
foreach (@sections) {
        if ( $plugin_cfg->param("$_.NAME") ) {
		# This appends a new option line to $selectlist
		$selectlist .= "<option value='".$plugin_cfg->param("$_.ID")."'>".$plugin_cfg->param("$_.NAME")."</option>\n";
	}
}
# Let the Var $selectlist with the name SELECTLIST be available in the template
$maintemplate->param( SELECTLIST => $selectlist );

###
# As an example: we create some vars for the template
###
$maintemplate->param( PLUGINNAME => $pname );
$maintemplate->param( ANOTHERNAME => "This is another Name" );


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
