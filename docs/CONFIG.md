# Config contract

A bench config is one JSON object:

```json
{"hit_cost_ms": 5.0, "drop_stopwords": true,
 "strategies": [{"kind": "exact"}, {"kind": "overlap", "params": {"threshold": 0.6}}]}
```

- `hit_cost_ms` is a finite positive number.
- every `kind` must be one of the registered strategies.
- `params` is an object; each strategy documents its own keys.

A violation raises `ConfigError` at load, naming the field or the strategy index. `default_config()`
compares every registered strategy and is the fallback when no file is passed.
