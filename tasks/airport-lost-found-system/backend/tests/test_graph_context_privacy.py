from app.models import LostReport, LostReportStatus, User, UserRole
from app.services.graph_context_service import GraphContextBuilder


def test_graph_context_masks_report_contact_details() -> None:
    passenger = User(id=7, name="Test Passenger", email="passenger@example.com", phone="+1 555 222 1234", password_hash="x", role=UserRole.passenger)
    report = LostReport(
        id=10,
        report_code="LR-ABC123",
        item_title="Passport holder",
        category="Passport",
        raw_description="Black holder",
        contact_email="passenger@example.com",
        contact_phone="+1 555 222 1234",
        status=LostReportStatus.open,
        passenger=passenger,
    )
    builder = GraphContextBuilder()

    builder.add_report(report)
    graph = builder.graph("test", "lost_report", 10, "privacy")
    report_node = next(node for node in graph["nodes"] if node["id"] == "lost_report:10")
    passenger_node = next(node for node in graph["nodes"] if node["id"] == "user:7")

    assert report_node["properties"]["contact_phone"] == "***-***-1234"
    assert report_node["properties"]["contact_email_domain"] == "example.com"
    assert passenger_node["properties"]["phone"] == "***-***-1234"
    assert "passenger@example.com" not in str(graph)
