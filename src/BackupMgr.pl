
package BackupMgr;
use POSIX qw/strftime/;
use YAML qw(LoadFile);
use Config::YAML;
use Date::Calc qw(Delta_Days Gmtime);

=item date_diff($)
Given a date in the form "YYYY_MM_DD", return the number of days between 
that date and the present.
=cut
sub date_diff($){
	my $saved_date = shift;
	my ($year,$month, $day) = split("_",$saved_date);
	my ($cur_year, $cur_month, $cur_day) = Gmtime;
	return abs(Delta_Days($year, $month, $day, $cur_year,$cur_month, $cur_day));
}

=item BackupMgr->__run_backup($$)
Run the actual commands to complete a specific backup by checking
to see if an old archive needs to be removed; removing it if so; and
then creating a new backup archive.
=cut

sub __run_backup($$$){
	my $__x = shift;
	my $_type = shift;
	my $backup_name = $__x->{conf}->{base_name};
	my $curr_date = BackupMgr::curr_date_string();
	my $snapshot = "$backup_name-$_type-$curr_date";

	if ($_type ne "daily" and $_type ne "monthly" and $_type ne "weekly"){
		return (-1, "$_type is an unrecognized backup _type");
	}
    #Make some convenience methods for accessing our hash.
	my $_num = "num_$_type";
	my $_blist = "$_type";
	my $_last = "last_$_type";


	if ($__x->{backups_data}->{$_num} >= $__x->{conf}->{$_type} ){
		my $oldest_snapshot = shift(@{$__x->{backups_data}->{$_blist}});
		my $del_cmd = $__x->{conf}->{del_cmd} . " $oldest_snapshot";
		logmsg( "Removing oldest archive: $del_cmd\n");
		system("$del_cmd");
	}		
#This is the first backup we're doing.
	$__x->{backups_data}->{$_last} = $curr_date;
	$__x->{backups_data}->{$_type} = [] if (! exists $__x->{backups_data}->{$_type});
	push(@{$__x->{backups_data}->{$_type}}, $snapshot);
	my $cmd = $__x->{conf}->{cmd} . " $snapshot " . join(' ',@{$__x->{conf}->{files}});
	logmsg( "Backing up: $cmd\n");
    my $retcode = system("$cmd");
	if ($retcode == 0){
        $__x->{backups_data}->{$_num} += 1;
    }
    my @retval = ($retcode, $__x->{backups_data});
	return \@retval;
} 

=item curr_date_string
Write the current GMT date as a string in the form "YYYY_MM_DD"
=cut
sub curr_date_string{

	my ($year, $month, $day) = Gmtime;

	my $ret = $year . "_" . $month . "_" . $day;
	return $ret;
}

=item new($)
Create and return an instance of Centrifuge, based on
the supplied configuration hash.
=cut
sub new {
	my $conf;
	my ($class, $arg) = @_;
	if ( ref($arg) ne "HASH"){
		die ("Must be passed reference to HASH");
	} else {
		$conf = $arg;
	}
	my $backups_hist_file = "history";
    my $backups_hist_dir = "/var/lib/BackupMgr";
    my $backups_hist_path = "$backups_hist_dir/$backups_hist_file";
	my $backup_name = $conf->{base_name};
    system("mkdir -p $backups_hist_dir");
	system("touch '$backups_hist_dir/$backups_hist_file'") if (! -e "$backups_hist_dir/$backups_hist_file");
	my $backup_hist = Config::YAML->new(config => $backups_hist_path, output => $backups_hist_path);
	my $backup_data = (exists $backup_hist->{$backup_name}) ? 
		$backup_hist->get($backup_name) 
		: {num_daily=>0, num_monthly=>0, num_weekly=>0};
	my $self = {conf => $conf, backups_data => $backup_data ,hist =>$backup_hist} ;
	return bless ($self, $class);
}

=item backup($)
Run the daily, weekly, and monthly backups specified by the configuration hash 
that this object was initialized with.

Write the history back out to the history file 
=cut
sub backup($){
	my $__x  = shift;
	my $backup_name = $__x->{conf}->{base_name};

	if (!exists($__x->{backups_data}->{last_daily}) or date_diff( $__x->{backups_data}->{last_daily}) >= 1){
#We need to do a daily backup
		$result = $__x->__run_backup("daily",$__x->{backups_data});
		if ($result->[0] == 0){
           $__x->{backups_data} = $result->[1];
		} else {
			logmsg( "Error in backup: $result->[1]\n");
		}
	} else {
		my $last = date_diff( $__x->{backups_data}->{last_daily});
		logmsg( "Skipped daily $backup_name backup... It's not time yet. It's only been $last days since the last backup \n");
		logmsg( "GMTime is: ".Gmtime." - last_daily is: ".$__x->{backups_data}->{last_daily}."\n");
	}

	if (!exists($__x->{backups_data}->{last_monthly}) or date_diff( $__x->{backups_data}->{last_monthly}) > 30){
#We need to do a monthly backup
		$result = $__x->__run_backup("monthly",$__x->{backups_data});
		if ($result->[0] == 0){
           $__x->{backups_data} = $result->[1];
		} else {
			logmsg( "Error in backup: $result->[1]\n");
		}
	} else {
		my $last = date_diff( $__x->{backups_data}->{last_daily});
		logmsg( "Skipped monthly $backup_name backup... It's not time yet. It's only been $last days since the last backup \n");
	}

	if (!exists($__x->{backups_data}->{last_weekly}) or date_diff( $__x->{backups_data}->{last_weekly}) >= 7){
#We need to do a weekly backup
		$result = $__x->__run_backup("weekly",$__x->{backups_data});
		if ($result->[0] == 0){
           $__x->{backups_data} = $result->[1];
		} else {
			logmsg( "Error in backup: $result->[1]\n");
		}
	} else {
		my $last = date_diff( $__x->{backups_data}->{last_daily});
		logmsg( "Skipped weekly $backup_name backup... It's not time yet. It's only been $last days since the last backup. \n");
	}

	$__x->{hist}->set($backup_name, $__x->{backups_data});
	$__x->{hist}->write;

}

=item logmsg($)
Print a formatted message to stdout
=cut
sub logmsg($){
 	print "[" . strftime('%d-%b-%Y %H:%M',localtime) . "]: " . join(' ',@_);
}

1;
