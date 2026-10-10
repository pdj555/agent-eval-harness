"""Oracle solutions for the hard task suite.

These exist to prove every hard task is solvable: tests/test_hard_tasks.py
runs each oracle against its task's pytest suite. The harness never sees
these; they are not used in any eval run.
"""

from __future__ import annotations

ORACLES: dict[str, str] = {}

ORACLES["fix-misleading-traceback"] = '''\
def _chunks(data, n):
    return [data[i:i + n] for i in range(0, len(data), n)]


def batch_process(records, batch_size):
    """Split records into batches and return per-batch checksums."""
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise ValueError(f"batch_size must be a positive int, got {batch_size!r}")
    results = []
    for chunk in _chunks(records, batch_size):
        checksum = sum(r["value"] for r in chunk) % 1000
        results.append(checksum)
    return results
'''

ORACLES["consolidate-order-module"] = '''\
def summarize_order(items):
    total_price = 0.0
    total_weight = 0.0
    for it in items:
        qty = it["qty"]
        total_price += it["price"] * qty
        total_weight += it["weight"] * qty
    return {
        "total_price": round(total_price, 2),
        "total_weight": round(total_weight, 2),
        "line_count": len(items),
    }
'''

ORACLES["dependency-toposort"] = '''\
class CircularDependencyError(Exception):
    pass


class UnknownPackageError(Exception):
    pass


def install_order(packages):
    order = []
    state = {}

    def visit(name):
        s = state.get(name, 0)
        if s == 2:
            return
        if s == 1:
            raise CircularDependencyError(f"cycle involving {name!r}")
        if name not in packages:
            raise UnknownPackageError(f"unknown package {name!r}")
        state[name] = 1
        for dep in packages[name]:
            visit(dep)
        state[name] = 2
        order.append(name)

    for name in packages:
        visit(name)
    return order
'''

ORACLES["fix-race-condition"] = '''\
import threading


class Counter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self.value += 1
'''

ORACLES["json-schema-validator"] = '''\
def validate(data, schema, path="$"):
    errors = []
    _check(data, schema, path, errors)
    return errors


def _check(data, schema, path, errors):
    t = schema.get("type")
    if t and not _type_ok(data, t):
        errors.append(f"{path}: expected {t}, got {type(data).__name__}")
        return
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: {data!r} not in enum {schema['enum']}")
    if t == "object" and isinstance(data, dict):
        for req in schema.get("required", []):
            if req not in data:
                errors.append(f"{path}.{req}: required property missing")
        for key, subschema in schema.get("properties", {}).items():
            if key in data:
                _check(data[key], subschema, f"{path}.{key}", errors)
    if t == "array" and isinstance(data, list):
        items_schema = schema.get("items", {})
        for i, item in enumerate(data):
            _check(item, items_schema, f"{path}[{i}]", errors)
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} below minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} above maximum {schema['maximum']}")


def _type_ok(data, t):
    return {
        "object": isinstance(data, dict),
        "array": isinstance(data, list),
        "string": isinstance(data, str),
        "integer": isinstance(data, int) and not isinstance(data, bool),
        "number": isinstance(data, (int, float)) and not isinstance(data, bool),
        "boolean": isinstance(data, bool),
        "null": data is None,
    }[t]
'''

ORACLES["log-parser-aggregator"] = '''\
def summarize_logs(lines):
    agg = {}
    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            continue
        _method, path, status_s, latency_s = parts
        try:
            status = int(status_s)
            latency = float(latency_s)
        except ValueError:
            continue
        endpoint = path.split("?", 1)[0]
        e = agg.setdefault(endpoint, {"count": 0, "total_latency": 0.0, "errors": 0})
        e["count"] += 1
        e["total_latency"] += latency
        if status >= 500:
            e["errors"] += 1
    return {
        ep: {
            "count": v["count"],
            "mean_latency_ms": v["total_latency"] / v["count"],
            "error_rate": v["errors"] / v["count"],
        }
        for ep, v in agg.items()
    }
'''
