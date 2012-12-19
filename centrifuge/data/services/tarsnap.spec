tarsnap:
  var_bin: "/usr/local/bin/tarsnap"
  cmd_create: "$var_bin $user_config --print-stats --humanize-numbers --one-file-system -cf $archive_name"
  cmd_delete: "$var_bin $user_config -df [$archive_name]"   
