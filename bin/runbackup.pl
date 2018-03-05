#!/usr/bin/perl

use LoxBerry::System;
use LoxBerry::Log;
use CGI;
use warnings;
use strict;

my $type;

# -----------------------------------------------------------
# Init logfile
# -----------------------------------------------------------

my $log = LoxBerry::Log->new ( name => 'backup', stdout => 1 );
LOGSTART "LoxBerry Backup";

# -----------------------------------------------------------
# Init config and parameters
# -----------------------------------------------------------

my $cgi = CGI->new;
$cgi->import_names('R');

my $pcfg = new Config::Simple("$lbpconfigdir/lbbackup.cfg");
if (! defined $pcfg) {
	LOGCRIT "Cannot open LoxBerry Backup config file $lbpconfigdir/lbbackup.cfg";
	notify($lbpplugindir, "Backup", "Cannot open LoxBerry Backup config file", "error");
	exit(1);
}

my %p = $pcfg->vars();

# Processing to read JIT settings
my $jit;
my $dest;

if (! is_enabled($R::scheduled)) {
	LOGOK "This backup is a Just-In-Time backup (not scheduled) -JIT options are used";
	$jit = 1;
	$R::type = $p{'JITBACKUP.TYPE'};
	$dest = $p{'JITBACKUP.DESTINATION'} ? $p{'JITBACKUP.DESTINATION'} : undef;
	LOGINF "* JIT Backuptype is $p{'JITBACKUP.TYPE'}";
	LOGINF "* JIT Destination is set to $dest" if ($dest); 
}







# -----------------------------------------------------------
# Check options
# -----------------------------------------------------------

$R::type = uc($R::type);

my @backuptypes = ( "DDZ", "TGZ", "RSYNC");

if ( ! grep( /^$R::type$/, @backuptypes ) ) {
  LOGCRIT "Backup type $R::type not supported";
  notify($lbpplugindir, "Backup", "Backup type $R::type not supported", "error");
  exit (1);
}

LOGDEB "Reading config of backup type R::type = $R::type";

# bc = Backup type config

my $bc = $pcfg->param(-block => "$R::type");


# -----------------------------------------------------------
# Calculate command line
# -----------------------------------------------------------
my @cmd;
@cmd = ("sudo",  "/usr/local/bin/raspiBackup.sh");

my $par_stopservices;
my $par_startservices;
my @params;
$dest = $dest ? $dest : $bc->{'DESTINATION'};
servicelist();

push @params, email_params() if is_enabled($p{'CONFIG.EMAIL_NOTIFICATION'});
push @params, "-F" if is_enabled($p{'CONFIG.FAKE_BACKUP'});
push @params, "-N", "fstab disk temp";
push @params, "-o", "\"$par_stopservices\"";
push @params, "-a", "\"$par_startservices\"";
push @params, "-k", $bc->{'RETENTION'};
push @params, "-t" , lc($R::type);
push @params, "-L", "current";

push @params, $dest;

#push  @params, "-z+";

my $paramstr;
foreach (@params) {
	$paramstr .= $_ . " ";
}
LOGDEB $paramstr;


# -----------------------------------------------------------
# Run Backup
# -----------------------------------------------------------

LOGINF "Changing to directory $lbplogdir";
chdir $lbplogdir;
LOGOK "Starting backup";
system(@cmd, @params);
my $exitcode = $? >> 8;
if ($exitcode != 0) {
	LOGERR "Backup failed with error code $exitcode";
} else {
	LOGOK "Backup was successful";
}

my %folderinfo = LoxBerry::System::diskspaceinfo($dest);

#$folderinfo{size}

 
LOGINF "Disk space info on $dest";
LOGINF "$folderinfo{filesystem} ($folderinfo{mountpoint}) | Size: " . formatSize(1024*$folderinfo{size}) . " | Used: " . formatSize(1024*$folderinfo{used}) . " | Free: " . formatSize(1024*$folderinfo{available});


print STDERR "Logfile-Name is " . $log->filename() . "\n";
exit;
		

# -----------------------------------------------------------
# Generate E-Mail Options
# -----------------------------------------------------------
sub email_params
{
	my $mailadr = "";
	my $friendlyname;
	
	print STDERR "Checking E-Mail notification...\n";
	$friendlyname = trim(lbfriendlyname() . " LoxBerry");
	my $mailcfg = new Config::Simple("$lbsconfigdir/mail.cfg");
	unless($mailadr = $mailcfg->param("SMTP.EMAIL"))
	{ 		
	print STDERR "Error reading mail configuration in $lbsconfigdir/mail.cfg\n";
	return;
	}
	return "-e", $mailadr, "-E", "-r $mailadr";
}

sub servicelist
{
	my (@stop_services_array) = $pcfg->param('CONFIG.STOPSERVICES');
	
	#print "Services array: " . $p{'CONFIG.STOPSERVICES'} . "\n";
	# print STDERR $p{'CONFIG.STOPSERVICES'};
	#$stop_services_list =~ s/\r//g;
	# my @stop_services_array = split(/,/, $stop_services_list);
	# Remove empty elements
	# @stop_services_array = grep /\S/, @stop_services_array;
	
	# print STDERR "\n" . $stop_services_array[0] . "\n";
	
	undef $par_stopservices;
	undef $par_startservices;
	
	foreach my $service (@stop_services_array) {
		# print "Service $service\n";
		$service = trim($service);
		if ($service) {
			$par_stopservices .= " service $service stop &&";
			$par_startservices .= " service $service start &&";
		}
	}
	# Remove trailing &&'s, or write : if empty
	$par_stopservices = $par_stopservices ? substr ($par_stopservices, 0, -3) : ":";
	$par_startservices = $par_startservices ? substr ($par_startservices, 0, -3) : ":";
	


}


sub formatSize {
        my $size = shift;
        my $exp = 0;

        my $units = [qw(B KB MB GB TB PB)];

        for (@$units) {
            last if $size < 1024;
            $size /= 1024;
            $exp++;
        }

        return wantarray ? ($size, $units->[$exp]) : sprintf("%.2f %s", $size, $units->[$exp]);
    }