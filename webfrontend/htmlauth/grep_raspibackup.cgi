#!/usr/bin/perl

use CGI::Carp qw(fatalsToBrowser);
use CGI qw/:standard/;
use warnings;
use strict;

print header;

my $pids = `pgrep raspiBackup.sh`;

my $nr_of_lines = $pids =~ tr/\n//;
print $nr_of_lines . "\n";
# print "1\n";
# print STDERR "grep raspibackup called - result $nr_of_lines processes.\n";