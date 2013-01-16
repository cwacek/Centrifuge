"""
Backup services are specified as yaml dictionaries with specified
commands. Available commands are:

create
  Create a new archive

delete
  Delete an archive

restore
  Recover an archive

Python (3) style named interpolation is allowed in the commands. There are
several universally defined variables that will be interpolated into commands
when they are run.  These are:

archive_name
  The name of the archive that's being dealt with. Usually interpolated
  by default.

In addition, variables can be specified in the service specification for
ease of use. This is done by declaring a *var_xxx* parameter, whose value
is then interpolated into any use of *var_xxx* that occurs in the service.

Example::

  tarsnap:
    var_bin: "/usr/local/bin/tarnsap"
    cmd_create: "$var_bin $user_config --print-stats --humanize-numbers --one-file-system -cf $archive_name"
    cmd_delete: "$var_bin $user_config -df $archive_name"

This defines the **tarsnap** service, with the commands *create* and
*delete*.
"""
import yaml
import logging
import subprocess
import string


log = logging.getLogger("centrifuge.service")

__ALL__ = [ "ServiceDefinitionError",
            "ServiceLoadError",
            "BackupService"
          ]

class ServiceLoadError(Exception):
  msg = "Treated '{0}' as {1}. Failed to load [{2}]"
  def __init__(self,arg,believed_type,err):
    self.msg.format(arg,believed_type,err)
    self.err = err

class ServiceDefinitionError(Exception):
  pass

class BackupService(object):
  """
  An abstraction of a backup service (whatever it may be),
  that can be used to backup/restore/delete archives.
  """

  commands = {
    "create": None,
    "delete": None,
    "restore": None
  }

  def __init__(self, name,cmds, spec_vars):
    """
    Build a BackupService object with the commands specified by
    *cmds*, with the variables specified by *spec_vars*.
    """

    self.name = name
    for command in self.commands:
      spec_key = "cmd_{0}".format(command)
      try:
        newcommand = cmds[spec_key]
      except KeyError:
        log.debug("Service '{0}' does not provide '{1}'".format(name,command))
      else:
        self.commands[command] = string.Template(newcommand).safe_substitute(spec_vars)

  def __getattr__(self,attr):
    try:
      return self.commands[attr]
    except KeyError:
      raise AttributeError("type object 'BackupService' has "
                           "no attribute '{0}'".format(attr))


  def trim(self,interval,local_state, keep):
    """
    Delete *interval* backups known in *state* until only *keep*
    newest are left.
    """
    okay = True
    candidates = local_state[interval]
    if len(candidates) <= keep:
      return

    for candidate in sorted(candidates,key=lambda x: x.date_created)[keep:]:
      del_cmd = string.Template(self.delete).safe_substitute(archive_name=str(candidate))
      try:
        result = subprocess.check_output(del_cmd.split(),stderr=subprocess.STDOUT)
      except subprocess.CalledProcessError,e:
        log.warn("Failed to trim archive '{0}' [{1}]".format(candidate,e))
        okay = False
      else:
        local_state[interval].remove(candidate)
        log.info("Trimmed {0}. ".format(candidate))
        log.debug("Service output: {0}".format(result))

    return okay


  def rotate(self,interval,local_state, files):
    """ Delete an old backup and add a new one """
    log.info("Rotating {0}".format(interval))
    okay=True
    to_delete = local_state.get_oldest(interval)

    del_cmd = string.Template(self.delete).safe_substitute(archive_name=str(to_delete))

    try:
      result = subprocess.check_output(del_cmd.split(),stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError,e:
      log.warn("Failed to remove '{0}' while rotating. [{1}]".format(
                      to_delete,e))
      okay=False
    else:
      local_state[interval].remove(to_delete)
      log.info("Removed {0}. ".format(to_delete))
      log.debug("Service output: {0}".format(result))

    self.add(interval,local_state, files)

    return okay


  def add(self,interval,local_state, files):
    """ Add a new backup instance via this service """
    okay=True

    newbackup = local_state.create_instance(interval)
    create_cmd = (string.Template(self.create)
                    .safe_substitute(archive_name=str(newbackup))
                    .split())
    create_cmd.extend(files)

    try:
      result = subprocess.check_output(create_cmd,stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError,e:
      log.warn("failed to add archive: [{0}]".format(e))
      okay=False
    else:
      log.info("Added {0}. ".format(newbackup))
      log.debug("Service Output: {0}".format(result))
      local_state.add_instance(newbackup)

    return okay


  @classmethod
  def LoadSpecs(cls,specs,userspec=None):
    """
    Returns a list of BackupServices loaded from
    the specification file *specs*.

    If *userspec* is defined, it should be a dict
    mapping service names to dictionaries of
    user variables for that service.
    """
    loaded = cls._load(specs)
    services =  cls._parse(loaded,userspec if userspec is not None else dict())

    return services

  @staticmethod
  def _load(spec):
    try:
      loaded_spec = yaml.safe_load(spec)
    except yaml.YAMLError, e:
      log.warn("Attempt to load '{0}' as file or string "
               "failed.".format(str(spec)))
      try:
        loaded_spec = yaml.safe_load(open(spec))
      except Exception,e:
        log.warn("Failed to load service specification '{0}'.".format(str(spec)))
        raise ServiceLoadError(spec,"filename",e)
    finally:
      if not loaded_spec:
        raise ServiceDefinitionError("Empty service specification")
      return loaded_spec # if we have one.

  @classmethod
  def _parse(classname,loaded_specfile,uservars=dict()):

    services = {}
    for service,details in loaded_specfile.iteritems():
      spec_vars = dict([(key,val)
                        for key,val
                        in details.iteritems()
                        if key.startswith("var_")])

      try:
        spec_vars.update(uservars[service])
      except TypeError:
        log.debug("Loading '{0}': No user variables provided.".format(service))
      except KeyError:
        log.debug("Loading '{0}': No user variables provided.".format(service))

      spec_cmds = dict([(key,val)
                        for key,val
                        in details.iteritems()
                        if key.startswith("cmd_")])

      try:
        service = classname(service,spec_cmds,spec_vars)
      except ServiceDefinitionError, e:
        raise e

      services[service.name] = service

    return services
