from __future__ import annotations

from chemgraph_chat.serialization import records_to_rows, serialize_value


class FakeNode(dict):
    def __init__(self, element_id: str, labels: set[str], **properties: str) -> None:
        super().__init__(properties)
        self.element_id = element_id
        self.labels = labels


class FakeRelationship(dict):
    def __init__(
        self,
        element_id: str,
        relationship_type: str,
        start_node: FakeNode,
        end_node: FakeNode,
        **properties: str,
    ) -> None:
        super().__init__(properties)
        self.element_id = element_id
        self.type = relationship_type
        self.start_node = start_node
        self.end_node = end_node


class FakePath:
    def __init__(self, nodes: list[FakeNode], relationships: list[FakeRelationship]) -> None:
        self.nodes = nodes
        self.relationships = relationships


class FakeRecord:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def data(self) -> dict[str, object]:
        return self._data


def test_serializes_node_relationship_and_path() -> None:
    carbon = FakeNode("1", {"Element"}, symbol="C", name="Carbon")
    reaction = FakeNode("2", {"Reaction"}, equation="C + O2 -> CO2")
    rel = FakeRelationship("3", "REACTANT", carbon, reaction, ratio="1")
    path = FakePath([carbon, reaction], [rel])

    serialized = serialize_value(path)

    assert serialized["type"] == "path"
    assert serialized["nodes"][0]["labels"] == ["Element"]
    assert serialized["relationships"][0]["relationship_type"] == "REACTANT"
    assert serialized["relationships"][0]["properties"] == {"ratio": "1"}


def test_records_to_rows_handles_empty_and_nested_values() -> None:
    assert records_to_rows([]) == []

    rows = records_to_rows(
        [
            FakeRecord(
                {
                    "drug": "Aspirin",
                    "nested": {"organisms": ["Human", "Mouse"]},
                }
            )
        ]
    )

    assert rows == [
        {
            "drug": "Aspirin",
            "nested": {"organisms": ["Human", "Mouse"]},
        }
    ]

