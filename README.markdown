Centrifuge
==========

What
----
A simple rotational backup system for Linux/Unix, designed for
tarsnap but intended to be service agnostic. Requires only that a
service supports the concept of adding and deleting archives.

Why?
----
I needed a lightweight way to do rotational backups. 

A Quick Warning
---------------

I built this for myself. Development code would be a good way to
describe it. If you want to use it, that would be awesome, but
understand that there might be bugs. If you do find bugs, please
tell me about them.

Install
-------
For now:

    $ git clone https://github.com/cwacek/Centrifuge
    $ cd Centrifuge
    $ python setup.py install

Configuring Centrifuge
----------
Setting up Centrifuge to work with one of the existing services
is as easy as defining your desired backup directories and
frequencies in a configuration file. 

Each backup job, or *archive*, is defined separately, although many can be
defined in a single file. For each *archive*, the configuration must specify
which files to backup (directories are handled recursively), which service to
use, and how many daily, weekly and monthly copies to keep.

A sample configuration file:

    ---
    mail:
      files:
        - /Users/johndoe/Mail
      service: tarsnap
      daily: 7
      weekly: 3
      monthly: 3
    documents:
      files:
        - /Users/johndoe/dinner_plans
        - /Users/johndoe/hotel_reservations
        - /Users/johndoe/a_single_file.txt
      service: tarsnap
      daily: 7
      weekly: 3
      monthly: 3

### Rotational Backup

While Centrifuge is designed to abstract away the notion of rotational backups,
if you don't run it at least once per day, then it can't work. The syntax for running Centrifuge is built into the command itself:

    centrifuge --help

Services
-------------------
Centrifuge operates using the notion of backup 'services', which
can be any application that can be run from the command line.
There is currently one built-in service, [Tarsnap][1], but more
can be defined by the user. 

### Built-in Services

-   Tarsnap

    Tarsnap is an encrypted backup service which you can read
    about [here][1]. The Centrifuge service requires you to
    define the following [User Variables]:

    -   `user_config`: User-specific configuration for Tarsnap,
        most importantly the path to the .tarsnaprc file

### Defining Services

Centrifuge becomes aware of services through YAML definition
files, which tell Centrifuge how to *create*, *delete*, and
*restore* files. Currently, *restore* is not supported as an
action (helpful I know). 

A defined service should provide commands for at least *create*
and *delete*. Here's an example for Tarsnap:

    tarsnap:
      cmd_create: "/usr/local/bin/tarsnap --print-stats --humanize-numbers --one-file-system -cf $archive_name"
      cmd_delete: "/usr/local/bin/tarsnap -df [$archive_name]"   

`$archive_name` is a special variable that is interpolated into
the command when Centrifuge runs (archives are auto-named,
although in an obvious fashion). 

Services can be defined in files in one of two places:
`~/.centrifuge/services/` and `/etc/centrifuge/services/`.

### Variables 
Centrifuge also supports both *service* and *user* variables in
service definitions.  

#### Service Variables 
Service variables are defined inside service
definitions and are local to that service. They can be used to
simplify service definitions. They are always named `var_xxx`
and will be interpolated into service commands where `var_xxx`
is found. For example

    tarsnap:
        var_bin: "/usr/local/bin/tarnsap"
        cmd_create: "$var_bin --print-stats --humanize-numbers --one-file-system -cf $archive_name"
        cmd_delete: "$var_bin -df $archive_name"

**Note:** Service variables will not currently be interpolated into
other service variable definitions.

#### User Variables

Often a backup command requires some sort of user specific
information to run. Centrifuge service definitions intentionally
do not hardcode this type of information to avoid the need to
write a specific service for every user. Instead, Centrifuge
supports the notion of *user* variables, which are defined by the
user as part of their configuration and then interpolated into
services when run. 

User variables are defined in the `~/.centrifuge/user.vars` file
as a yaml dictionary. They are scoped by service, so namespacing
is not an issue. An example user variable file is the following:

    tarsnap:
      user_config: "--configfile /Users/johndoe/.tarsnaprc"

That file defines one user variable named `user_config` for the
`tarsnap`. None of our previous service definitions for Tarsnap
made use of this variable, but here is an example of one that
does (and this incidentally is the actual built-in service
definition):

    tarsnap:
        var_bin: "/usr/local/bin/tarnsap"
        cmd_create: "$var_bin $user_config --print-stats --humanize-numbers --one-file-system -cf $archive_name"
        cmd_delete: "$var_bin $user_config -df $archive_name"


[1]: https://www.tarsnap.com

