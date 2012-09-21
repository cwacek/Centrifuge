tarsnap:
  var_bin: "/usr/local/bin/tarnsap"
  cmd_create: "{var_bin} {config} --print-stats --humanize-numbers --one-file-system -cf {archive_name}"
  cmd_delete: "{var_bin} {config} -df [archive_name}]"   
