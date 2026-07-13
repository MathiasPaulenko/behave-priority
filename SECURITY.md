# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a vulnerability

If you discover a security vulnerability in `behave-priority`, please report it responsibly.

**Do not open a public GitHub issue.**

Instead, email **security@paulenko.dev** with:

1. A description of the vulnerability
2. Steps to reproduce (minimal example)
3. Potential impact
4. Suggested fix (if any)

You will receive a response within 48 hours. If the vulnerability is confirmed, a fix will be released as soon as possible and you will be credited (unless you prefer to remain anonymous).

## Security considerations

### What behave-priority does

- Reorders scenario execution by parsing `@priority(N)` tags from `scenario.tags`
- Uses `scenario.skip()` to skip scenarios when fail-fast triggers
- Modifies behave's runner feature list in-place during `before_all`

### What behave-priority does NOT do

- Does not execute arbitrary code from tags
- Does not modify files on disk
- Does not make network requests
- Does not access environment variables or secrets

### Tag parsing

Priority tags are parsed with strict regex validation. Invalid tags raise `PriorityParseError` — they never silently produce unexpected behavior.

### Thread safety

`PriorityQueue` uses `threading.Lock` for thread-safe operations. The sorter and hooks are not designed for concurrent access to the same runner instance.
