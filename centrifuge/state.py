import centrifuge
from datetime import date
import yaml
import logging
log = logging.getLogger("centrifuge.state")

class StateParseError(Exception):
  pass

class PropertyDict(dict):

  def __getattr__(self,key):
    try:
      return self.__getitem__(key)
    except KeyError:
      raise AttributeError(
            "PropertyDict has no attribute '{0}'".format(key))

class BackupInstance(yaml.YAMLObject):
  
  def __init__(self,archive_name, interval, date_created=None):
    self.name = archive_name
    self.interval =interval
    self.date_created = date.today() if not date_created else date_created

  def __repr__(self):
    return ("{{name: {0}, created: {1}, interval: {2}}}"
                .format(self.name,self.date_created,self.interval))

  def __str__(self):
    return "{0}_{2}_{1}".format(self.name,
                                self.interval,
                                self.date_created.strftime("%d-%m-%y"))

  @classmethod
  def to_yaml(cls,dumper,data):
    return dumper.represent_mapping(
                mapping={
                      'name': data.archive_name,
                      'interval': data.interval,
                      'date_created': data.date_created
                      })

class State(PropertyDict):

  def __init__(self,backup_name,statedict=None):
    self.backup_name = backup_name
    if statedict:
      try:
        self.parse(statedict)
      except Exception, e:
        raise 
    else:
      self['daily'] = []
      self['weekly'] = []
      self['monthly'] = []

  def add_instance(self,interval):
    """Add a backup instance to this state object"""
    newinstance = BackupInstance(self.backup_name,interval)
    self[interval].append(newinstance)

    latest_key = "last_{0}".format(interval)
    self[latest_key] = newinstance
    
    return newinstance

  def get_oldest(self,interval):
    return sorted(self[interval],key=lambda x: x.date_created)[0]

  @classmethod
  def ParseFile(cls,statefilepath):
    try:
      with open(statefilepath) as statefile:
        try:
          yamlobj = yaml.load(statefile.read())
          
        except yaml.YAMLError,e:
          raise StateParseError("Unable to parse state. [{0}]".format(e))
    except IOError,e:
      if e.errno == 2:
# The file doesn't exist. That's okay
        log.info("Statefile '{0}' doesn't exist. Will create".format(statefilepath))
        return dict()
    except Exception, e:
      raise centrifuge.CentrifugeFatalError("Fatal")
    else:
      return yamlobj

  def parse(self,statedict):
    """
    Parse the state from a YAML dict
    """
    KEYS = ['daily','monthly','weekly']
    for key in KEYS:
      try:
        self[key] = statedict['key']
        last_key = "last_{0}".format(key)
        try:
          self[last_key] = statedict[last_key]
        except KeyError:
          # There is no known last backup. That's fine.
          pass
      except KeyError:
        raise CentrifugeFatalError("Couldn't find '{0}' key in statefile".format(key))


  
