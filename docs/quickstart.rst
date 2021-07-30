Quickstart
==========

Now would be time to quickly mention that, while Dimsum is text based,
the best experience is delivered be using the browser. A lot of effort
is expended to ensure that terminal based connections still work and,
more importantly, are useful but many advanced features and especially
editing and creating are more fun with the browser at your disposal.

Back to the game. As you may have guessed, that while everything is an
object in Dimsum, that means there must be different kinds. This is
true, but it's also important to remember that behavior can be
bestowed upon anything. Objects are all just objeects in the end, with
various metadata used to guide things, provide defaults, and allow for
easier categorization and debugging.

Kinds Of Objects
================

**Thing**

Items on the ground, tools, food, toys, games, knick-nacks, doo-dads,
gadgets and just about most things are, well, things.

**Area**

Objects where people can be and navigate too and from. Otherwise they
behave mostly like containers as you can drop things in them. When
things happen publicly they're usually only visible to people in the
same area.

**Exit**

These are basically **Things** with one additional behavior and that's
managing a link to another area. This is the area people end up in
after they attempt to `go` to/through/via them.

**Alive**

As well as things, these objects are also created with health behavior
and memory.

This is useful to know because they form the basis of the commands
related to creation.

More Examples
=============

.. prompt:: bash >

    go north

Picking thigns up.

.. prompt:: bash >

    hold box


Tips and Tricks
===============

Commonly used idioms, commands, and other useful things that aren't
immediately obvious to easy to discover.

#. Are you lost?

#. Trying to refer to an object and it's not having it?

#. Need more information about a thing?
