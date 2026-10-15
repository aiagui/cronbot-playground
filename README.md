# cronbot-playground
Sandbox repository for Cronbot autonomous software engineering

## Duration formatting

`format_duration(seconds)` converts a non-negative whole number of seconds into
a compact, human-readable duration such as `1m 5s` or `2h 3m 4s`. It raises
`TypeError` for non-integers and `ValueError` for negative values.
