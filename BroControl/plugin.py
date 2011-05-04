#
# BroControl Plugin API.
#

import pluginreg
import config
import util
import doc

Registry = pluginreg.PluginRegistry()

class Plugin:
    """The class ``Plugin`` is the base class for all BroControl plugins.

    The class has a number of methods for plugins to override, and every
    plugin must at least override ``name()`` and ``version()``.

    For each BroControl command ``foo``, there's are two methods,
    ``cmd_foo_pre`` and ``cmd_foo_post``, that are called just before the
    command is executed and just after it has finished, respectivey. The
    arguments these methods receive correspond to their command-line
    parameters, and are further documented belows.

    The ``cmd_<XXX>_pre`` methods have the ability to prevent the command's
    execution, either completely or partially for those commands that take
    nodes as parameters. In the latter case, the method receives a list of
    nodes that the command is to be run on, and it can filter that list and
    returns modified version of nodes actually to use. The standard case would
    be returning simply the unmodified ``nodes`` parameter. To completely
    block the command's execution, return an empty list. To just not execute
    the command for a subset, remove them affected ones.  For commands that do
    not receive nodes as arguments, the return value is interpreted as boolean
    indicated whether command execution should proceed (True) or not (False).

    The ``cmd_<XXX>_post`` methods likewise receive the commands arguments as
    their parameter, as documented below. For commands taking nodes, the list
    corresponds to those nodes for which the command was actually executed
    (i.e., after any ``cmd_<XXX>_pre`` filtering). Each node is given as a
    tuple ``(node, bool)`` with *node* being the actual `Node`_, and the boolean
    indicating whether the command was succesful for it.

    Note that if plugin prevents a command from execution either completely or
    partially, it should report its reason via the ``message*(`` or
    ``error()`` methods.

    If multiple plugins hook into the same command, all their
    ``cmd_<XXX>_{pre,post}`` are executed in undefined order. The command is
    executed on the intersection of all ``cmd_<XXX>_pre`` results.

    Finally, note that the ``restart`` command doesn't have its own method as
    it's just a combination of other commands and thus their callbacks are
    run.
    """

    @doc.api
    def getGlobalOption(self, name):
        """Returns the value of the global BroControl option *name*. If the
        user has not set the options, its default value is returned."""
        if config.Config.hasAttr(name):
            raise KeyError

        return config.Config.__getattr(name)

    @doc.api
    def getOption(self, name):
        """Returns the value of one of the plugin's options, *name*. The
        returned value will always be a string.

        An option has a default value (see *options()*), which can be
        overridden by a user in ``broctl.cfg``. An option's value cannot be
        changed by the plugin.
        """
        name = "%s.%s" % (self.prefix().lower(), name.lower())

        if not config.Config.hasAttr(name):
            raise KeyError

        return config.Config.__getattr__(name)

    @doc.api
    def getState(self, name):
        """Returns the current value of one of the plugin's state variables,
        *name*. The returned value will always be a string. If it has not yet
        been set, an empty string will be returned.

        Different from options, state variables can be set by the plugin and
        are persistent across restarts. They are not visible to the user.

        Note that a plugin cannot query any global BroControl state variables.
        """
        name = "%s.state.%s" % (self.prefix().lower(), name.lower())

        if not config.Config.hasAttr(name):
            return ""

        return config.Config.__getattr__(name)

    @doc.api
    def setState(self, name, value):
        """Sets the one of the plugin's state variables, *name*, to *value*.
        *value* must be a string. The change is permanent and will be recorded
        to disk.

        Note that a plugin cannot change any global BroControl state
        variables.
        """
        if not isinstance(value, str):
            self.error("values for a plugin state variable must be strings")

        if "." in name or " " in name:
            self.error("plugin state variable names must not contain dots or spaces")

        name = "%s.state.%s" % (self.prefix().lower(), name.lower())
        config.Config._setState(name, value)

    @doc.api
    def getNodes(self, names):
        """Returns `Node`_ objects for a string of space-separated node names.
        If a name does not correspond to know node, an error message is
        printed and the node is skipped from the returned list. If not names
        are known, an empty list is returned."""
        nodes = []

        for arg in names.split():
            h = config.Config.nodes(arg, True)
            if not h:
                util.output("unknown node '%s'" % arg)
            else:
                nodes += [h]

        return nodes

    @doc.api
    def message(self, msg):
        """Reports a message to the user."""
        util.output(msg, prefix="plugin:%s" % self.prefix())

    @doc.api
    def debug(self, msg):
        """Logs a debug message in BroControl' debug log if enabled."""
        util.debug(1, msg, prefix="plugin:%s" % self.prefix())

    @doc.api
    def error(self, msg):
        """Reports an error to the user."""
        error("error: %s" % msg, prefix="plugin:%s" % self.prefix())

    @doc.api
    def execute(self, node, cmd):
        """Executes a command on the given *node* of type `Node`_. Returns a
        tuple ``(rc, output)`` in which ``rc`` is the command's exit code and
        ``output`` the combined stdout/stderr output."""
        control.executeCmdsParallel([node, cmd])

    @doc.api
    def nodes(self):
        """Returns a list of all configured `Node`_ objects."""
        return config.Config.nodes()

    @doc.api
    def hosts(self):
        """Returns a list of all hosts running at least one node configured in
        ``nodes.cfg``"""
        return config.Config.hosts()

    @doc.api
    def executeParallel(self, cmds):
        """Executes a set of commands in parallel on multiple nodes. ``cmds``
        is a list of tuples ``(node, cmd)``, in which the *node* is `Node`_
        instance and *cmd* a string with the command to execute for it. The
        method returns a list of tuples ``(node, rc, output)``, in which
        ``rc`` is the exit code and ``output`` the combined stdout/stderr
        output for the corresponding ``node``."""
        control.executeCmdsParallel(cmds)

    ### Methods that must be overridden by plugins.

    @doc.api("override")
    def name(self):
        """Returns a a strings with a descriptive *name* for the plugin (e.g.,
        ``"TestPlugin"``). The name must not contain any white-space.

        This method must be overridden by derived classes. The implementation
        must not call the parent class' implementation.
        """
        raise NotImplementedError

    @doc.api("override")
    def version(self):
        """
        Returns an integer with a version number for the plugin. Plugins
        should increase their version number with any significant change.

        This method must be overridden by derived classes. The implementation
        must not call the parent class' implementation.
        """
        raise NotImplementedError

    @doc.api("override")
    def prefix(self):
        """Returns a string with a prefix for the plugin's options and
        commands names (e.g., "myplugin")``).

        This method can be overridden by derived classes. The implementation
        must not call the parent class' implementation. The default
        implementation returns a lower-cased version of *name()*.
        """
        return self.name().lower()

    @doc.api("override")
    def options(self):
        """Returns a set of local configuration options provided by the
        plugin.

        The return value is a list of 4-tuples each having the following
        elements:

            ``name``
                A string with name of the option (e.g., ``Path``). Option
                names are case-insensitive. Note that the option name exposed
                to the user will be prefixed with your plugin's prefix as
                returned by *name()* (e.g., ``myplugin.Path``).

            ``type``
                A string with type of the option, which must be one of
                ``"bool"``, ``"string"``, or ``"int"``.

            ``default``
                A string with the option's default value. Note that this must
                always be a string, even for non-string types. For booleans,
                use ``"0"`` for False and ``"1"`` for True. For integers, give
                the value as a string ``"42"``.

            ``description``
                A string with a description of the option semantics.

        This method can be overridden by derived classes. The implementation
        must not call the parent class' implementation. The default
        implementation returns an empty list.
        """
        return []

    @doc.api("override")
    def commands(self):
        """Returns a set of custom commands provided by the
        plugin.

        The return value is a list of 2-tuples each having the following
        elements:

            ``command``
                A string with the command's name. Note that command name
                exposed to the user will be prefixed with the plugin's prefix
                as returned by *name()* (e.g., ``myplugin.mycommand``).

            ``description``
                A string with a description of the command's semantics.


        This method can be overridden by derived classes. The implementation
        must not call the parent class' implementation. The default
        implementation returns an empty list.
        """
        return []

    @doc.api("override")
    def nodeKeys(self):
        """Returns a list of custom keys for ``node.cfg``. The value for a
        keys will be available from the `Node`_ object as attribute
        ``<prefix>_<key>`` (e.g., ``node.test_mykw``). If not set, the
        attribute will be set to None.

        This method can be overridden by derived classes. The implementation
        must not call the parent class' implementation. The default
        implementation returns an empty list.
        """
        return []

    @doc.api("override")
    def analyses(self):
        """Returns a custom list of analyses to be controlled by the
        ``analysis`` command.

        Each analysis entry is a 4-tuple consistent of the following items:

            ``name``
                A string with a short name for the analysis.

            ``description``
                A string describing the analysis.

            ``mechanism``

                A 2-tuple of strings defining mechanism to use for toggling
                the analysis. Possible values are:

                ``("unload", "<script>")``
                    A Bro script that will be *unloaded* when the
                    analysis is disabled. Note that it will *not* be
                    automatically loaded when the analysis is enabled,
                    that still needs to be done by the normal
                    site-specific policy.

                ``("bool", "<var>")``
                    A Bro script-level variable ``<var>`` of boolean type
                    controls whether the analysis is performed. BroControl
                    will set the boolean to True if the analysis is enabled,
                    and to False if it disabled.

                ``("bool-inv", "<var>")``
                    Like ``bool:<var>``, except that semantics are inverted:
                    BroControl will set the boolean to True if the analysis is
                    disabled, and to False if it enabled.

                ``("events", "<group>")``
                    Defines a Bro event group that corresponds to this
                    analysis. BroControl will enable the event group if the
                    analysis is enables, and disable it otherwise.

                ``("link", "<name>")``
                    Links another analysis controlled by the ``analysis``
                    command to this one. If this one is enabled, the other
                    will be enabled as well. If this one is disabled, the
                    other will be disabled as well.

                ``("enable", "<name>")``
                    If analysis is enabled, the analysis ``<name>>`` is so as
                    well.

                ``("disable", "<name>")``
                    If analysis is disabled, the analysis ``<name>>`` is so as
                    well.

                ``mechanism`` can also be a list of such 2-tuples to specify
                more than one entry for an analysis.

        This method can be overridden by derived classes. The implementation
        must not call the parent class' implementation. The default
        implementation returns an empty list.
        """
        return []

    @doc.api("override")
    def init(self):
        """Called once just before BroControl starts executing any commands.
        This method can do any initialization that the plugin may require.

        Note that at when this method executes, BroControl guarantees that all
        internals are fully set up (e.g., user-defined options are available).
        This may not be the case when the class ``__init__`` method runs.

        Returns a boolean, indicating whether the plugin should be used. If it
        returns ``False``, the plugin will be removed and no other methods
        called.

        This method can be overridden by derived classes. The default
        implementation always returns True.
        """
        return True

    @doc.api("override")
    def done(self):
        """Called once just before BroControl terminates. This method can do
        any cleanup the plugin may require.
        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        return

    @doc.api("override")
    def cmd_nodes_pre(self):
        """Called just before the ``nodes`` command is run.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_nodes_post(self):
        """Called just after the ``nodes`` command has finished.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_config_pre(self):
        """Called just before the ``config`` command is run.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_config_post(self):
        """Called just after the ``config`` command has finished.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_exec_pre(self, cmdline):
        """Called just before the ``exec`` command is run. *cmdline* is a
        string with the command line to execute.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_exec_post(self, cmdline):
        """Called just after the ``exec`` command has finished. Arguments are
        as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_install_pre(self):
        """Called just before the ``install`` command is run.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_install_post(self):
        """Called just after the ``install`` command has finished.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_cron_pre(self, arg):
        """Called just before the ``cron`` command is run. *arg* is None if
        the cron is executed without arguments. Otherwise, it is one of
        strings ``enable``, ``disable``, or ``?``.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_cron_post(self, arg):
        """Called just after the ``cron`` command has finished. Arguments are 
        as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_analysis_pre(self, enable, type):
        """Called just before the ``analysis`` command is run. *enable* is a
        boolean that is True if an analysis being enabled, and False if
        disabled. *type* is a string with the name of the analysis.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_analysis_post(self, enable, type):
        """Called just after the ``analysis`` command has finished.  Arguments
        are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_check_pre(self, nodes):
        """Called just before the ``check`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_check_post(self, results):
        """Called just after the ``check`` command has finished. It receives
        the list of 2-tuples ``(node, bool)`` indicating the nodes the command
        was executed for, along with their success status.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_start_pre(self, nodes):
        """Called just before the ``start`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_start_post(self, results):
        """Called just after the ``start`` command has finished. It receives
        the list of 2-tuples ``(node, bool)`` indicating the nodes the command
        was executed for, along with their success status.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_stop_pre(self, nodes):
        """Called just before the ``stop`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_stop_post(self, results):
        """Called just after the ``stop`` command has finished. It receives
        the list of 2-tuples ``(node, bool)`` indicating the nodes the command
        was executed for, along with their success status.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_status_pre(self, nodes):
        """Called just before the ``status`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_status_post(self, nodes):
        """Called just after the ``status`` command has finished.  Arguments
        are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_update_pre(self, nodes):
        """Called just before the ``update`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_update_post(self, results):
        """Called just after the ``update`` command has finished. It receives
        the list of 2-tuples ``(node, bool)`` indicating the nodes the command
        was executed for, along with their success status.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_custom(self, cmd, args):
        """Called when command defined by the ``commands`` method is executed.
        ``cmd`` is the command (with the plugin's prefix), and ``args`` is a
        single *string* with all arguments.

        If the arguments are actually node names, ``getNodes`` can
        be used to get the `Node`_ objects.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_df_pre(self, nodes):
        """Called just before the ``df`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_df_post(self, nodes):
        """Called just after the ``df`` command has finished. Arguments are as
         with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_diag_pre(self, nodes):
        """Called just before the ``diag`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_diag_post(self, nodes):
        """Called just after the ``diag`` command has finished. Arguments are
        as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_attachgdb_pre(self, nodes):
        """Called just before the ``attachgdb`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_attachgdb_post(self, nodes):
        """Called just after the ``attachgdb`` command has finished. Arguments
         are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_peerstatus_pre(self, nodes):
        """Called just before the ``peerstatus`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_peerstatus_post(self, nodes):
        """Called just after the ``peerstatus`` command has finished. 
        Arguments are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_netstats_pre(self, nodes):
        """Called just before the ``netstats`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_netstats_post(self, nodes):
        """Called just after the ``netstats`` command has finished. Arguments
         are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_top_pre(self, nodes):
        """Called just before the ``top`` command is run. It receives the list
        of nodes, and returns the list of nodes that should proceed with the
        command. Note that when ``top`` is run interactively to auto-refresh
        continously, this method will be called once before each update.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_top_post(self, nodes):
        """Called just after the ``top`` command has finished. Arguments are
        as with the ``pre`` method. Note that when ``top`` is run
        interactively to auto-refresh continously, this method will be called
        once after each update.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_restart_pre(self, nodes, clean):
        """Called just before the ``restart`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command. *clean* is boolean indicating whether the ``--clean``
        argument has been given.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_restart_post(self, results):
        """Called just after the ``restart`` command has finished. It receives
        the list of 2-tuples ``(node, bool)`` indicating the nodes the command
        was executed for, along with their success status. The remaining
        arguments are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_restart_pre(self, nodes, clean):
        """Called just before the ``restart`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command. *clean* is boolean indicating whether the ``--clean``
        argument has been given.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_restart_post(self, results):
        """Called just after the ``restart`` command has finished. It receives
        the list of 2-tuples ``(node, bool)`` indicating the nodes the command
        was executed for, along with their success status. The remaining
        arguments are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_restart_pre(self, nodes, clean):
        """Called just before the ``restart`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command. *clean* is boolean indicating whether the ``--clean``
        argument has been given.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_restart_post(self, results):
        """Called just after the ``restart`` command has finished. It receives
        the list of 2-tuples ``(node, bool)`` indicating the nodes the command
        was executed for, along with their success status. The remaining
        arguments are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_cleanup_pre(self, nodes, all):
        """Called just before the ``cleanup`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command. *all* is boolean indicating whether the ``--all``
        argument has been given.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_cleanup_post(self, nodes, all):
        """Called just after the ``cleanup`` command has finished. Arguments
        are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_capstats_pre(self, nodes, interval):
        """Called just before the ``capstats`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command. *integer* is an integer with the measurement interval in
        seconds.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_capstats_post(self, nodes, interval):
        """Called just after the ``capstats`` command has finished. Arguments
        are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_scripts_pre(self, nodes, full_path, check):
        """Called just before the ``scripts`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command. ``full_path`` and ``check`` are boolean indicating
        whether the ``-p`` and ``-c`` options were given, respectively.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_scripts_post(self, nodes, full_path, check):
        """Called just after the ``scripts`` command has finished. Arguments
        are as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_print_pre(self, nodes, id):
        """Called just before the ``print`` command is run. It receives the
        list of nodes, and returns the list of nodes that should proceed with
        the command. *is* is a string with the name of the ID to printed.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    @doc.api("override")
    def cmd_print_post(self, nodes, id):
        """Called just after the ``print`` command has finished. Arguments are
        as with the ``pre`` method.

        This method can be overridden by derived classes. The default
        implementation does nothing.
        """
        pass

    # Internal methods.

    def _registerOptions(self):
        if ( not self.prefix() ):
            self.error("plugin prefix must not be empty")

        if "." in self.prefix() or " " in self.prefix():
            self.error("plugin prefix must not contain dots or spaces")

        for (name, ty, default, descr) in self.options():
            if ( not name ):
                self.error("plugin option names must not be empty")

            if "." in name or " " in name:
                self.error("plugin option names must not contain dots or spaces")

            if not isinstance(default, str):
                self.error("plugin option default must be a string")

            config.Config._setOption("%s.%s" % (self.prefix().lower(), name), default)
