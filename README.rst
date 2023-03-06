Debug Library for Robot Framework
=================================

.. contents::
   :local:

Introduction
------------

This Library is a Fork by René Rohner from the original robotframework-debuglibrary by Xie Yanbo


Robotframework-DebugLibrary is a debug library for `RobotFramework`_,
which can be used as an interactive shell(REPL) also.

.. _`RobotFramework`: http://robotframework.org/

.. image:: https://api.codeclimate.com/v1/badges/5201026ff11b63530cf5/maintainability
   :target: https://codeclimate.com/github/xyb/robotframework-debuglibrary/maintainability
   :alt: Maintainability

.. image:: https://api.codeclimate.com/v1/badges/5201026ff11b63530cf5/test_coverage
   :target: https://codeclimate.com/github/xyb/robotframework-debuglibrary/test_coverage
   :alt: Test Coverage

.. image:: https://github.com/xyb/robotframework-debuglibrary/workflows/test/badge.svg?branch=master
   :target: https://github.com/xyb/robotframework-debuglibrary
   :alt: test

.. image:: https://img.shields.io/pypi/v/robotframework-debuglibrary.svg
   :target: https://pypi.org/project/robotframework-debuglibrary/
   :alt: Latest version

.. image:: https://img.shields.io/badge/robotframework-3%20%7C%204%20%7C%205-blue
   :target: https://github.com/xyb/robotframework-debuglibrary
   :alt: Support robotframework versions

.. image:: https://img.shields.io/pypi/pyversions/robotframework-debuglibrary
   :target: https://github.com/xyb/robotframework-debuglibrary
   :alt: Support python versions

.. image:: https://img.shields.io/pypi/dm/robotframework-debuglibrary
   :target: https://pypi.org/project/robotframework-debuglibrary/
   :alt: PyPI Downloads

.. image:: https://img.shields.io/pypi/l/robotframework-debuglibrary.svg
   :target: https://github.com/xyb/robotframework-debuglibrary/blob/master/LICENSE
   :alt: License


Installation
------------

To install using ``pip``::

    pip install robotframework-debug

NOTICE: 2.0 is not compatible with python 2
*******************************************

``DebugLibrary`` >= 2.0.0 supports Python versions 3.x only.

    pip install 'robotframework-debug'

Usage
-----

You can use this as a library, import ``DebugLibrary`` and call ``Debug``
or ``Debug If`` keywords in your test files like this::

    *** Settings ***
    Library         DebugLibrary

    ** test case **
    SOME TEST
        # some keywords...
        Debug
        # some else...
        ${count} =  Get Element Count  name:div_name
        Debug If  ${count} < 1

Or you can run it standalone as a ``RobotFramework`` shell::

    $ rfdebug
    [...snap...]
    >>>>> Enter interactive shell
    > help
    Input Robotframework keywords, or commands listed below.
    Use "libs" or "l" to see available libraries,
    use "keywords" or "k" to see the list of library keywords,
    use the TAB keyboard key to autocomplete keywords.

    Documented commands (type help <topic>):
    ========================================
    EOF  continue  docs  help  keywords  libs  ll        n     pdb  selenium
    c    d         exit  k     l         list  longlist  next  s    step
    > log  hello
    > get time
    < '2011-10-13 18:50:31'
    > # use TAB to auto complete commands
    > BuiltIn.Get Time
    < '2011-10-13 18:50:39'
    > import library  String
    > get substring  helloworld  5  8
    < 'wor'
    > # define variables as you wish
    > ${secs} =  Get Time  epoch
    # ${secs} = 1474814470
    > Log to console  ${secs}
    1474814470
    > @{list} =  Create List    hello    world
    # @{list} = ['hello', 'world']
    > Log to console  ${list}
    ['hello', 'world']
    > &{dict} =  Create Dictionary    name=admin    email=admin@test.local
    # &{dict} = {'name': 'admin', 'email': 'admin@test.local'}
    > Log  ${dict.name}
    > # print value if you input variable name only
    > ${list}
    [u'hello', u'world']
    > ${dict.name}
    admin
    > # start a selenium server quickly
    > help selenium
    Start a selenium webdriver and open url in browser you expect.

            s(elenium)  [<url>]  [<browser>]

            default url is google.com, default browser is firefox.
    > selenium  google.com  chrome
    # import library  SeleniumLibrary
    # open browser  http://google.com  chrome
    < 1
    > close all browsers
    > Ctrl-D
    >>>>> Exit shell.

The interactive shell support auto-completion for robotframework keywords and
commands. Try input ``BuiltIn.`` then type ``<TAB>`` key to feeling it.
The history will save at ``~/.rfdebug_history`` default or any file
defined in environment variable ``RFDEBUG_HISTORY``.

In case you don't remember the name of keyword during using ``rfdebug``,
there are commands ``libs`` or ``ls`` to list the imported libraries and
built-in libraries, and ``keywords <lib name>`` or ``k`` to list
keywords of a library.

``rfdebug`` accept any ``pybot`` arguments, but by default, ``rfdebug``
disabled all logs with ``-l None -x None -o None -L None -r None``.

Step debugging
**************

``DebugLibrary`` support step debugging since version ``2.1.0``.
You can use ``step``/``s``, ``next``/``n``, ``continue``/``c``,
``list``/``l`` and ``longlist``/``ll`` to trace and view the code
step by step like in ``pdb``::

    $ robot some.robot
    [...snap...]
    >>>>> Enter interactive shell
    > l
    Please run `step` or `next` command first.
    > s
    .> /Users/xyb/some.robot(7)
    -> log to console  hello
    => BuiltIn.Log To Console  hello
    > l
      2   	Library  DebugLibrary
      3
      4   	** test case **
      5   	test
      6   	    debug
      7 ->	    log to console  hello
      8   	    log to console  world
    > n
    hello
    .> /Users/xyb/some.robot(8)
    -> log to console  world
    => BuiltIn.Log To Console  world
    > c
    >>>>> Exit shell.
    world

Note: Single-step debugging does not support ``FOR`` loops currently.

Submitting issues
-----------------

Bugs and enhancements are tracked in the `issue tracker
<https://github.com/xyb/robotframework-debuglibrary/issues>`_.

Before submitting a new issue, it is always a good idea to check is the
same bug or enhancement already reported. If it is, please add your comments
to the existing issue instead of creating a new one.

Development
-----------

If you want to develop and run DebugLibrary locally, you can use ::

    $ python DebugLibrary/shell.py tests/step.robot

`shell.py` is calling `robot` through a child process, so it will interrupt
python debugging capabilities. If you want to debug in tools like vscode,
pdb, you should run ::

    $ python -m robot tests/step.robot

If you want to run the test, please install the dependency packages first
and then execute the test ::

    $ python setup.py develop
    $ python setup.py test

Since RF takes over stdout, debugging information can be output with ::

    import sys
    print('some information', file=sys.stdout)

License
-------

This software is licensed under the ``New BSD License``. See the ``LICENSE``
file in the top distribution directory for the full license text.

.. # vim: syntax=rst expandtab tabstop=4 shiftwidth=4 shiftround
