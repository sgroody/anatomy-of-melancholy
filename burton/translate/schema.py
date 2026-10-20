"""JSON schema for one packet's model output (passed to `claude -p --json-schema`)."""

ENTRY = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "translation", "literal", "confidence", "flags", "note", "self_translation", "source"],
    "properties": {
        "id": {"type": "string"},
        "translation": {"type": "string"},
        "literal": {"type": ["string", "null"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "flags": {"type": "array", "items": {"type": "string", "enum": [
            "corrupt-text", "misquotation-suspected", "wordplay", "technical-medical", "truncated"]}},
        "note": {"type": ["string", "null"]},
        "self_translation": {
            "type": "object", "additionalProperties": False, "required": ["status", "burton_quote"],
            "properties": {
                "status": {"type": "string", "enum": ["none", "full", "partial", "paraphrase"]},
                "burton_quote": {"type": ["string", "null"]},
            },
        },
        "source": {
            "type": "object", "additionalProperties": False,
            "required": ["status", "author", "work", "locus", "basis"],
            "properties": {
                "status": {"type": "string", "enum": ["burton-cites", "probable", "unidentified"]},
                "author": {"type": ["string", "null"]},
                "work": {"type": ["string", "null"]},
                "locus": {"type": ["string", "null"]},
                "basis": {"type": ["string", "null"]},
            },
        },
    },
}

PACKET_OUTPUT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["passages"],
    "properties": {"passages": {"type": "array", "items": ENTRY}},
}
