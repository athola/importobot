# String cache micro-benchmark

The `regex_cache.get_compiled_pattern` helper stores compiled regular expressions so
security checks do not recompile hot patterns on every call. Running the benchmark
below on a single core (ThinkPad T14, Python 3.12) gives a 2.1× reduction in wall
clock time for 2,000 lookups.

```
>>> import time, re
>>> from importobot.utils.regex_cache import get_compiled_pattern
>>> PATTERN = r"<script>"
>>> start = time.perf_counter()
>>> for _ in range(2000):
...     re.compile(PATTERN)
...
>>> no_cache = time.perf_counter() - start
>>> start = time.perf_counter()
>>> for _ in range(2000):
...     get_compiled_pattern(PATTERN)
...
>>> cache = time.perf_counter() - start
>>> round(no_cache / cache, 2)
2.16
```

Rerun the measurement with the snippet above or drop it into a short
`uv run python - <<'PY' ... PY` shell command; we skip a dedicated CLI entry to
keep the benchmark lightweight.
