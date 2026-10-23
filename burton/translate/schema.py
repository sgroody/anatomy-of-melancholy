"""JSON schema for one packet's model output (passed to `claude -p --json-schema`)."""

FLAGS = ["corrupt-text", "misquotation-suspected", "wordplay", "technical-medical", "truncated",
         "language-mismatch", "boundary-suspect"]

ENTRY = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "translation", "literal", "confidence", "flags", "note", "glosses", "self_translation",
                 "source"],
    "properties": {
        "id": {"type": "string"},
        "translation": {"type": "string"},
        "literal": {"type": ["string", "null"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "flags": {"type": "array", "items": {"type": "string", "enum": FLAGS}},
        "note": {"type": ["string", "null"]},
        "glosses": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False, "required": ["word", "sense"],
                "properties": {"word": {"type": "string"}, "sense": {"type": "string"}},
            },
        },
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
