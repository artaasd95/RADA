from rada.tools.schemas import TOOL_SCHEMAS


def test_tool_schema_shapes() -> None:
    assert len(TOOL_SCHEMAS) >= 5
    for schema in TOOL_SCHEMAS:
        assert schema["type"] == "function"
        fn = schema["function"]
        assert "name" in fn
        assert "parameters" in fn
        assert fn["parameters"]["type"] == "object"
