"""Small JSON Schema subset validator for packaged harness contracts."""

from __future__ import annotations

from typing import Any


def json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_json_schema_subset(data: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(json_type_matches(data, str(item)) for item in expected_types):
            errors.append(f"{path}: expected type {'|'.join(str(item) for item in expected_types)}")
            return errors

    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: value {data!r} not in enum")

    if isinstance(data, str) and "minLength" in schema and len(data) < int(schema["minLength"]):
        errors.append(f"{path}: string shorter than minLength {schema['minLength']}")

    if isinstance(data, (int, float)) and not isinstance(data, bool) and "minimum" in schema:
        if data < schema["minimum"]:
            errors.append(f"{path}: number below minimum {schema['minimum']}")

    if isinstance(data, list):
        if "minItems" in schema and len(data) < int(schema["minItems"]):
            errors.append(f"{path}: array has fewer than minItems {schema['minItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(data):
                errors.extend(validate_json_schema_subset(item, item_schema, f"{path}[{index}]"))

    if isinstance(data, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                errors.append(f"{path}: missing required property {key}")
        if schema.get("additionalProperties") is False and isinstance(properties, dict):
            for key in data:
                if key not in properties:
                    errors.append(f"{path}: unexpected property {key}")
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key in data and isinstance(child_schema, dict):
                    errors.extend(validate_json_schema_subset(data[key], child_schema, f"{path}.{key}"))
    return errors
