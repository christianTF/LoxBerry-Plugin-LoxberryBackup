#!/usr/bin/perl

use LoxBerry::System;
use LoxBerry::Log;
use CGI;
use warnings;
use strict;

my $type;

my $output;
my $exitcode;

# $LoxBerry::System::DEBUG=1;


# -----------------------------------------------------------
# Init logfile
# -----------------------------------------------------------

my $log = LoxBerry::Log->new ( package => $lbpplugindir, name => 'backup', stdout => 1 );
LOGSTART "LoxBerry Backup";

# -----------------------------------------------------------
# Init config and parameters
# -----------------------------------------------------------

my $cgi = CGI->new;
$cgi->import_names('R');
$R::scheduled if (0);

my $pcfg = new Config::Simple("$lbpconfigdir/lbbackup.cfg");
if (! defined $pcfg) {
	LOGCRIT "Cannot open LoxBerry Backup config file $lbpconfigdir/lbbackup.cfg";
	LOGEND;
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
	$log->logtitle("Just-In-Time Backup $p{'JITBACKUP.TYPE'}");
} else {
	$log->logtitle("Scheduled Backup ". uc($R::type));
}

# Locking
if ($jit) {
	LOGINF "Prepare JIT lock";
	my $status = LoxBerry::System::lock(lockfile => 'lbbackup');
	if ($status) {
		LOGCRIT "LoxBerry Backup is locked. It seems that another backup is running. Exiting.";
		LOGEND;
		exit(1);
	}
} else {
	LOGINF "Prepare schedule lock";
	my $status;
	for (my $x = 0; $x < 120; $x++) {
		$status = LoxBerry::System::lock(lockfile => 'lbbackup', wait => 180);
		last if (! $status);
		LOGINF "Lock lbbackup - Try $x of 120 (3 minutes each). Further waiting";
	}
	if ($status) {
		LOGCRIT "Could not lock LoxBerry Backup after 120 tries (3 min. each) . It seems that another backup is running. Giving up.";
		LOGEND;
		exit (1);
	}
}

my $starttime_hr = currtime('hr');
my $starttime_iso = currtime('iso');

# -----------------------------------------------------------
# Check options
# -----------------------------------------------------------

$R::type = uc($R::type);

my @backuptypes = ( "DDZ", "TGZ", "RSYNC");

if ( ! grep( /^$R::type$/, @backuptypes ) ) {
  LOGCRIT "Backup type $R::type not supported";
  LOGEND;
  notify($lbpplugindir, "Backup", "Backup type $R::type not supported", "error");
  exit (1);
}

LOGDEB "Reading config of backup type R::type = $R::type";

# bc = Backup type config

my $bc = $pcfg->param(-block => "$R::type");


# -----------------------------------------------------------
# Calculate command line
# -----------------------------------------------------------

my $loglevel = LoxBerry::System::pluginloglevel();
print "Loglevel is $loglevel\n";
my @cmd;
@cmd = ("sudo",  "/usr/local/bin/raspiBackup.sh");

my $par_stopservices;
my $par_startservices;
my @params;
$dest = $dest ? $dest : $bc->{'DESTINATION'};

qx { ls $dest };
sleep 1;

if (! -e $dest) {
	LOGINF "Destination directory does not exist - try to create...";
	$output = qx { mkdir -p $dest };
	$exitcode  = $? >> 8;
	if($exitcode != 0) {
		LOGCRIT "Error creating destination directory: $output";
		LOGEND;
		notify($lbpplugindir, "Backup", "Cannot create destination directory $dest. No permissions? Error $output", "error");
		exit(1);
	}
	LOGOK "Destination directory was created.";
	qx { chown loxberry:loxberry $dest };
}

servicelist();

push @params, email_params() if is_enabled($p{'CONFIG.EMAIL_NOTIFICATION'});
push @params, "-F" if is_enabled($p{'CONFIG.FAKE_BACKUP'});
push @params, "-N", '"fstab disk temp"';
push @params, "-o", '"' . trim($par_stopservices) . '"';
push @params, "-a", '"' . trim($par_startservices) . '"';
push @params, "-k", $bc->{'RETENTION'};
push @params, "-t", lc($R::type);
push @params, "-z-" if($R::type eq 'RSYNC');
push @params, "-L", "current";
push @params, "-l", "debug" if ($loglevel == 7);
push @params, "-m", "minimal" if ($loglevel <= 5);
push @params, "-m", "detailed" if ($loglevel > 5);
push @params, "-v" if ($loglevel == 7);

push @params, $dest;

#push  @params, "-z+";

my $paramstr;
foreach (@cmd) {
	$paramstr .= $_ . " ";
}

foreach (@params) {
	$paramstr .= $_ . " ";
}

# $paramstr = "script --append " . $log->filename() . ";

# -----------------------------------------------------------
# Run Backup
# -----------------------------------------------------------

LOGINF "Changing to directory $lbplogdir";
chdir $lbplogdir;
LOGOK "Starting backup";
LOGINF "$paramstr";
my $logname = $log->close;
system("script --quiet --flush --return --append " . $log->filename() . " --command '" . $paramstr . "'");
# qx { @cmd @params };
$exitcode = $? >> 8;
# # Copy logfile to $log object
# if (-e "$lbplogdir/raspiBackup.log") {
	# open ( my $fh, "<", "$lbplogdir/raspiBackup.log" ); 
	# while ( my $line = <$fh> ) {
		# print $logfh $line;
	# }
	# close $fh;
# }

$log->open();

if ($exitcode != 0) {
	LOGERR "Backup failed with error code $exitcode";
} else {
	LOGOK "Backup was successful";
}

my $endtime_hr = currtime('hr');
my $endtime_iso = currtime('iso');

my $runtime_str = "Backup started at " . $starttime_hr . " and finished at " . $endtime_hr;
LOGINF $runtime_str;

my %folderinfo = LoxBerry::System::diskspaceinfo($dest);

#$folderinfo{size}

my $diskspaceinfo; 
$diskspaceinfo = "Disk space info on $dest\n";
$diskspaceinfo .= "$folderinfo{filesystem} ($folderinfo{mountpoint}) | Size: " . formatSize(1024*$folderinfo{size}) . " | Used: " . formatSize(1024*$folderinfo{used}) . " | Free: " . formatSize(1024*$folderinfo{available});
LOGINF $diskspaceinfo;

print STDERR "Logfile-Name is " . $log->filename() . "\n";

# -----------------------------------------------------------
# LoxBerry Notify
# -----------------------------------------------------------

my %notification = (
            PACKAGE => $lbpplugindir,                    # Mandatory
            NAME => "Backup",                            # Mandatory        
            LOGFILE => $log->filename
    );



if ($exitcode == 0) {
	$notification{'MESSAGE'} = "LoxBerry Backup has successfully finished.\n";
	$notification{'SEVERITY'} = 6;
} 
if ($exitcode != 0) {
	$notification{'MESSAGE'} = "LoxBerry Backup finished with error. See the logfile for details.\n";
	$notification{'SEVERITY'} = 3;
} 

$notification{'MESSAGE'} .= $runtime_str . "\n" . $diskspaceinfo;

if (is_enabled($p{'CONFIG.NOTIFY_BACKUP_INFOS'}) && $exitcode == 0 || 
	is_enabled($p{'CONFIG.NOTIFY_BACKUP_ERRORS'}) && $exitcode != 0 ) {
	LoxBerry::Log::notify_ext( \%notification );
}

LoxBerry::System::unlock(lockfile => 'lbbackup');
LOGEND;
exit;
		

# -----------------------------------------------------------
# Generate E-Mail Options
# -----------------------------------------------------------
sub email_params
{
	my $mailadr = "";
	my $friendlyname;
	
	$friendlyname = trim(lbfriendlyname() . " LoxBerry");
	
	# LoxBerry 1.4 mail.json
	if (-e "$lbsconfigdir/mail.json") {
		eval {
			require LoxBerry::JSON;
			my $jsonobj = LoxBerry::JSON->new();
			my $mcfg = $jsonobj->open(filename => "$lbsconfigdir/mail.json", readonly => 1);
			$mailadr = $mcfg->{SMTP}->{EMAIL};
		};
	} elsif (-e "$lbsconfigdir/mail.cfg") {
		eval {
			my $mailcfg = new Config::Simple("$lbsconfigdir/mail.cfg");
			$mailadr = $mailcfg->param("SMTP.EMAIL");
		};
	}
	
	if ($mailadr eq "") { 		
		LOGWARN "raspiBackup mail notification is enabled, but no LoxBerry mail configuration is done - skipping sending e-mails";
		return;
	}
	
	LOGOK "LoxBerry mail configuration read for raspiBackup e-mails.";
	
	# The -E parameter currently does not work in raspiBackup
	#return ("-e", $mailadr, "-E \"-r $mailadr\"");
	
	return ("-e", $mailadr);
	
}

sub servicelist
{
	my (@stop_services_array) = $pcfg->param('CONFIG.STOPSERVICES');
	
	undef $par_stopservices;
	undef $par_startservices;
	
	foreach my $service (@stop_services_array) {
		# print "Service $service\n";
		$service = trim($service);
		if ($service) {
			$par_stopservices .= "systemctl stop $service && ";
			$par_startservices .= "systemctl start $service && ";
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