Exceptions
==========

The exceptions module defines the custom exception hierarchy for
``behave-priority``.

.. autoclass:: behave_priority.exceptions.PriorityError
   :members:
   :show-inheritance:

.. autoclass:: behave_priority.exceptions.PriorityParseError
   :members:
   :show-inheritance:

Hierarchy
---------

.. code-block:: text

   Exception
   └── PriorityError
       └── PriorityParseError

PriorityError
-------------

Base exception for all ``behave-priority`` errors. Catch this when you want
to handle any error from the library:

.. code-block:: python

   from behave_priority import PriorityError

   try:
       # ... priority operations ...
   except PriorityError as e:
       print(f"Priority error: {e}")

PriorityParseError
------------------

Raised when a priority tag has invalid syntax. This includes:

- ``@priority(abc)`` — non-integer value
- ``@priority(1.5)`` — floating-point value
- ``@priority()``
- ``@feature-priority(abc)`` — same issues for feature-level tags

.. code-block:: python

   from behave_priority import PriorityParseError

   try:
       parse_priority(["priority(abc)"])
   except PriorityParseError as e:
       print(f"Invalid tag: {e}")

The error message includes the invalid tag for debugging purposes.
