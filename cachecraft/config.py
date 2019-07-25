"""Strategy configuration.

A bench config is a JSON document that names the strategies to compare and the
global replay knobs. It lets you version the exact experiment alongside the
trace so a report is reproducible.

Config schema
-------------
::

    {
      "hit_cost_ms": 5.0,
      "drop_stopwords": true,
      "strategies": [
        { "kind": "exact" },
        { "kind": "prefix",  "params": { "words": 5 } },
        { "kind": "overlap", "params": { "threshold": 0.6 } },
        { "kind": "route",   "params": { "threshold": 0.55 } }
      ]
