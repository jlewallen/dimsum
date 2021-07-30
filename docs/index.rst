Dimsum
======

A Python based engine for text-based, collaboratively designed dynamic
worlds. A slightly different take on traditional MOOs and MUDs. In
these worlds everything is an object with customizable behavior.

An Example
==========

Examples can go a long way, especially as many people aren't familiar
with archaic Internet culture. After logging in the user is greeted
and then presented with a prompt. Here's an example of the kind of
greeting you might see:

.. code-block:: none

	Town Courtyard

	A quaint, small town courtyard. Trees overhang the cobblestone
	sidewalks that segment the green. A damp, smokey smell wafts
	through the air. Along the edges of a large, well maintained
	parkland, there are several small, older buildings. Some of them
	appear to be very new and a few look embarrassingly modern.

	You can tell it's an easy place to ask for help and that people
	are eager for you to look around and, when you're comfortable,
	even go places.

What happened was the system automatically issued a `look` command and
this is the response. You can try it yourself by typing `look` and
hitting *ENTER*.

.. prompt:: bash >

    look

You should see the same response as you got after logging in. Great!
Oh, there's so much more! You can navigate, hold things, drop things,
create things, create new areas, contribute to the description of
things, and even give custom behavior to any of the things/places you
create!


.. toctree::
   :maxdepth: 2
   :caption: Links:

   quickstart
   WelcomePage.md
   GettingStarted.md
   BeginnersCreation.md
   BeginnersEditing.md
   DesignPhilosophy.md
   EventHandlers.md
   BehindTheScenes.md
   source/modules

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
