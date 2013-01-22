import os
import sys
import datetime
import yaml
import logging
import logging.handlers
import pkg_resources

logging.basicConfig(level=logging.INFO,format='%(name)-12s: %(levelname)-8s %(message)s')
log = logging.getLogger('centrifuge')

formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')

import service
from config import BackupConfig,ServiceNotAvailableError
import state

class CentrifugeFatalError(Exception):
  pass

class Centrifuge(object):

  DATA_DIR = "/var/lib/centrifuge"
  DEFAULT_SERVICES = [(service,pkg_resources.resource_string(__name__,"data/services/{0}".format(service)))
                          for service
                          in pkg_resources.resource_listdir(__name__,"data/services")
                     ]
  ADDL_SERVICE_DIRS = [ os.path.expanduser("~/.centrifuge/services"),
                        "/etc/centrifuge/services"
                      ]
  USER_SPEC_DIR = os.path.expanduser("~/.centrifuge")

  STATEFILE = "{0}/state".format(DATA_DIR)
  TIMEDELTAS = {
    'daily': datetime.timedelta(days=1),
    'weekly': datetime.timedelta(days=7),
    'monthly': datetime.timedelta(days=30)
  }

  def config_required(func):
    def _decorator( self, *args, **kwargs):
      if not self.config_file:
        raise CentrifugeFatalError('Configuration file required for this command')

      self.config = BackupConfig(self.config_file)
      self.config.check_services(self.supported_services())
      func(self,*args, **kwargs)
    return _decorator


  @classmethod
  def _userpath(cls,path):
    return "{0}/{1}".format(cls.USER_SPEC_DIR,path)

  def supported_services(self,printout=False):
    if printout:
      print("Supported Services:")
      for srv in self.services.itervalues():
        print("  - {0}\n".format(srv.name))
    return [srv.name for srv in self.services.itervalues()]

  def __init__(self):
    self._setup_datadir()

  @config_required
  def run_backups(self,*args,**kwargs):
    cm_args = kwargs['args']
    success = []
    for backup in cm_args.backup_name:
      log.info("Running backup '{0}'".format(backup))
      success.append(self.run_backup(backup))
      if not success[-1]:
        log.info("'{0}' was not completely successful".format(backup))

    return all(success)

  def run_backup(self,backup_name):
    try:
      backup_config = self.config[backup_name]
    except KeyError as e:
      log.warn("No configured backup with name '{0}'".format(backup_name))
    else:

      try:
        backup_state = self.state[backup_name]
      except KeyError:
        self.state[backup_name] = state.State(backup_name)
        backup_state = self.state[backup_name]

      bservice = self.services[ backup_config['service'] ]
      ok_daily = self.try_backup(bservice,backup_config,backup_state,"daily")
      ok_weekly = self.try_backup(bservice,backup_config,backup_state,"weekly")
      ok_monthly = self.try_backup(bservice,backup_config,backup_state,"monthly")

      with open(self.STATEFILE,'w') as statef:
        yaml.dump(self.state,statef)

      return all((ok_monthly,ok_daily,ok_weekly))


  def try_backup(self,bservice, bconfig,bstate,interval):
    """ Attempt to perform a backup at interval. Fail if you shouldn't """

    latest_key = "last_{0}".format(interval)
    try:
      latest_created = bstate[latest_key].date_created
    except KeyError:
      latest_created = datetime.date(year=1900,month=1,day=1)

    if (datetime.date.today() - latest_created) >= self.TIMEDELTAS[interval]:
      if len(bstate[interval]) > bconfig[interval]:
        okay = bservice.trim(interval,bstate)
      elif len(bstate[interval]) == bconfig[interval]:
        okay = bservice.rotate(interval,bstate,bconfig['files'])
      else:
        okay = bservice.add(interval,bstate,bconfig['files'])
    else:
      okay = True
      log.info("Skipping '{0}' interval. It's only been {1}".format(
                  interval,
                  datetime.date.today() - latest_created))

    return okay

  def _setup_datadir(self):
    """
    Setup the /var/lib/centrifuge data directory and load
    our state file.
    """

    log.debug("Setting up data directory '{0}'".format(self.DATA_DIR))
    if not os.path.exists(self.DATA_DIR):
      try:
        os.makedirs(self.DATA_DIR)
      except OSError,e:
        raise CentrifugeFatalError("Unable to create data directory: {0}".format(e[1]))

    self.state = state.State.ParseFile(self.STATEFILE)

  def _load_user_vars(self,location):
    """
    Load any user defined variables from `~/.centrifuge/user.vars`
    """
    path = os.path.expanduser(location)
    if not os.path.exists(path):
      log.warn("Couldn't find any user variables in '{0}'".format(path))
    else:
      try:
        uservars = yaml.safe_load(open(path))
      except yaml.YAMLError,e:
        raise CentrifugeFatalError("Failed to parse user variable file.")
      except IOError:
        raise CentrifugeFatalError("Failed while trying to read user variable file.")
      else:
        return uservars

  def _load_services(self,uservars=None,additional_dirs=[]):
    """
    Load services from a couple of locations. First the built in services,
    then any additional ones specified.
    """
    services = {}

    for service_name,service_file in self.DEFAULT_SERVICES:
      try:
        services.update(service.BackupService.LoadSpecs(service_file,uservars))
      except service.ServiceDefinitionError,e:
        log.error("Error parsing built-in service '{0}': {1}".format(service_name,e))

    for addl_dir in additional_dirs:
      for service_file in os.listdir(addl_dir):
        fname = addl_dir + "/" + service_file
        try:
          services.update(service.BackupService.LoadSpecs(fname,uservars))
        except service.ServiceDefinitionError,e:
          log.error("Error parsing user service '{0}': {1}".format(fname,e))
        except service.ServiceLoadError,e:
          pass

    return services

  @config_required
  def list_backups(self,*args,**kwargs):
    """
    List the configured backups that we know about.
    """
    print("Configured Backups")
    for config in self.config.iterconfig():
      print(config[0])
      print("="*len(config[0]))
      print(BackupConfig.prettyprint(config[1]))
      print("")

  def list_services(self,**kwargs):
    """
    List the available backup services we have
    """
    self.supported_services(printout=True)

  def act(self):
    import argparse
    container = argparse.ArgumentParser(add_help=False)
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("-c","--config",type=str,
                   help="Backup Configuration File",
                   required=True)
    p.add_argument("--uservars",
                   help="User variable specification file (Default ~/.centrifuge/user.vars)",
                   default="~/.centrifuge/user.vars")
    vbose = argparse.ArgumentParser(add_help=False)
    vbose.add_argument("-v",action="store_true",
                   help="Be verbose")

    subp = container.add_subparsers(description="Commands")
    runp = subp.add_parser("run",parents=[p,vbose],
                           help="Run configured backups")
    runp.add_argument("backup_name",nargs="+")
    runp.set_defaults(func=self.run_backups)

    lsp = subp.add_parser("list_services",parents=[vbose],
                          help="List the available backup services")
    lsp.set_defaults(func=self.list_services)

    lsb = subp.add_parser("list_backups",parents=[p],
                          help="List the configured backups")
    lsb.set_defaults(func=self.list_backups)

    state.State.make_parser(self.state,subp,parents=[vbose])

    args = container.parse_args()
    self.config_file = getattr(args,"config",None)

    user_spec_vars = self._load_user_vars(args.uservars)
    # Look for services in our additional locations.
    addl_svc_dir = filter( os.path.exists, self.ADDL_SERVICE_DIRS)
    self.services = self._load_services(user_spec_vars,addl_svc_dir)

    if args.v:
      log.setLevel(logging.DEBUG)

    try:
      return args.func(args=args,state=self.state)
    except ServiceNotAvailableError, e:
      log.error(e)
      return -1;



def run():
  try:
    ok = Centrifuge().act()
    if ok:
      sys.exit(0)
    else:
      sys.exit(1)
  except CentrifugeFatalError,e:
    log.error("{0}".format(e))

if __name__ == 'main':
  run()
