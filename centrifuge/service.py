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

config
  Universal configuration string intended to provide user specific 
  requirements. For example, for **tarsnap** it may be necessary to 
  add '--configfile /home/bobjones/.tarsnaprc' to every command. 

  This value often comes from user-defined service specification addons.

archive_name
  The name of the archive that's being dealt with. Usually interpolated 
  by default.

In addition, variables can be specified in the service specification for
ease of use. This is done by declaring a *var_xxx* parameter, whose value
is then interpolated into any use of *var_xxx* that occurs in the service.

Example::

  tarsnap:
    var_bin: "/usr/local/bin/tarnsap"
    cmd_create: "$var_bin $config --print-stats --humanize-numbers --one-file-system -cf $archive_name"
    cmd_delete: "$var_bin $config -df $archive_name"

This defines the **tarsnap** service, with the commands *create* and
*delete*. The ``var_bin`` notation is explained further below.
"""
import yaml
import logging
import string

log = logging.getLogger("centrifuge.service")

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
        log.info("Service '{0}' does not provide '{1}'".format(name,command))
      else:
        self.commands[command] = string.Template(newcommand).safe_substitute(spec_vars) 

  def __getattr__(self,attr):
    try:
      return self.commands[attr]
    except KeyError:
      raise AttributeError("type object 'BackupService' has "
                           "no attribute '{0}'".format(attr))



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
    services =  cls._parse(loaded,userspec)
    
    return services

  @staticmethod
  def _load(spec):
    try:
      loaded_spec = yaml.safe_load(spec)
    except yaml.YAMLError, e:
      log.info("Attempt to load '{0}' as file or string " 
               "failed.".format(str(spec)))
      try:
        loaded_spec = yaml.safe_load(open(specfile))
      except Exception,e:
        log.warn("Failed to load service specification '{0}'.".format(str(spec)))
        raise ServiceLoadError(spec,"filename",e)
    finally:
      return loaded_spec # if we have one.

  @classmethod
  def _parse(classname,loaded_specfile,uservars):
    services = []
    for service,details in loaded_specfile.iteritems():
      spec_vars = dict([(key,val) 
                        for key,val 
                        in details.iteritems() 
                        if key.startswith("var_")])

      try:
        spec_vars.update(uservars[service])
      except TypeError:
        log.info("Loading '{0}': No user variables provided.".format(service))
      except KeyError:
        log.info("Loading '{0}': No user variables provided.".format(service))

      spec_cmds = dict([(key,val) 
                        for key,val 
                        in details.iteritems() 
                        if key.startswith("cmd_")]) 

      try:
        service = classname(service,spec_cmds,spec_vars)
      except ServiceDefinitionError, e:
        raise e
      
      services.append(service)

    return services


     
    

    
