#!/usr/bin/perl -w 

use lib qw(/usr/local/share/perl/5.10.1/);
use lib qw(/usr/lib/perl5);
use lib qw(/opt/local/lib/perl5/site_perl/5.12.3/);
use YAML qw(LoadFile);
use Config::YAML;
use Date::Calc qw(Delta_Days Gmtime);
use FindBin;                                        
use lib "$FindBin::Bin";
my $config_path = "" . $FindBin::Bin . "/backup_conf.yml";
my $conf = Config::YAML->new(config =>"$config_path");
require "$FindBin::Bin/BackupMgr.pl";



foreach my $backup (sort keys %$conf){
	next if ($backup eq "_infile" or $backup eq "_outfile" or $backup eq "_strict"	);
	my $next_conf = $conf->get($backup);
	print "Backing up $conf->{$backup}->{base_name} \n";
	my $mgr = new BackupMgr($next_conf);
	$mgr->backup();
}

exit  0;


