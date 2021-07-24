# Event Handlers

There are several ways to listen to and respond to things happening in the
world around your entities. Typically this will take the shape of an event
handler of some kind.

## Scheduled Events

It's extremely common to need a regularly scheduled event to trigger some
periodic process. The `Purple Line Train` is a good example of that kind of
thing. Because of the nerdy origins of dimsum this means dealing with
cron-based scheduling.

### Cron

Cron is basically a format for specifying how often a scheduled task should
happen. It's extremely flexible and common, as well as being impossible to
understand.
 
To provide cron based scheduling, dimsum uses the [croniter](https://pypi.org/project/croniter/#usage) Python library. In
addition to supporting the standard cron syntax other features are available,
like hashed and random expressions.
