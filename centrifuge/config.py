import yaml
import os
import logging
import pkg_resources
log = logging.getLogger('centrifuge.config')

class InvalidConfigurationError(Exception):
  pass

class ServiceNotAvailableError(Exception):

  def __str__(self):
    return "Configuration requested backup service '{0}', which is not available."

class BackupConfig(dict):

  RX_SCHEMA = pkg_resources.resource_string(__name__,"data/config_schema.rx")

  @staticmethod
  def validate(configobj):
    import rx.Rx as rx
    rx_validator = rx.Factory(
                        { "register_core_types": True}
                    ).make_schema(
                          yaml.safe_load(BackupConfig.RX_SCHEMA)
                      )
    valid = []
    for name,config in configobj.iteritems():
      if not rx_validator.check(config):
        log.warn("Failed to validate '{0}'".format(name))
        valid.append(False)
      else:
        valid.append(True)

    return valid

  def __init__(self,configfile):
    config = yaml.safe_load(open(configfile))
    validated = BackupConfig.validate(config)
    if all(validated):
      self.update(config)
    else:
      raise InvalidConfigurationError("{0}".format(
                  [c for i,c in enumerate(config) if not validated[i]]))

  @staticmethod
  def prettyprint(conf):
    template = """
Service: {service}
Files: 
  {files}
# Monthly: {monthly}
# Weekly: {weekly}
# Daily: {daily}
"""
    
    pp = template.format(
            service = conf['service'],
            files = "\n\t".join(conf['files']),
            monthly= conf['monthly'] if 'monthly' in conf else "0",
            weekly=conf['weekly'] if 'weekly' in conf else "0",
            daily=conf['daily'] if 'daily' in conf else "0"
          )
    return pp

  def iterconfig(self):
    for config in self:
      yield (config,self[config])


  def add_config(self,configfile):
    config = yaml.safe_load(open(configfile))
    validated = BackupConfig.validate(config)
    if all(validated):
      self.update(config)
    else:
      raise InvalidConfigurationError("{0}".format(
                  [c for i,c in enumerate(config) if not validated[i]]))

  def check_services(self,available):
    """
    Check if the configurations loaded into this object are compatible
    with the services in `available`.
    """
    for name,config in self.iterconfig():
      if config['service'] not in available:
        raise ServiceNotAvailableError(config['service'])

  
  


