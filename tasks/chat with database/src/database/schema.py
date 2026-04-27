"""Known schema definitions for the Chinook-style CSV dataset."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Numeric, String, Table


@dataclass(slots=True)
class ColumnDefinition:
    """Represents one database column in a table definition."""

    name: str
    type_: object
    nullable: bool = True
    primary_key: bool = False
    foreign_key: str | None = None


@dataclass(slots=True)
class TableDefinition:
    """Represents one CSV-backed table to be created in the database."""

    name: str
    columns: list[ColumnDefinition]
    description: str
    business_notes: list[str] = field(default_factory=list)


CHINOOK_TABLES: list[TableDefinition] = [
    TableDefinition(
        name="Artist",
        description="Musical artists referenced by albums and tracks.",
        columns=[
            ColumnDefinition("ArtistId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("Name", String(120)),
        ],
    ),
    TableDefinition(
        name="Album",
        description="Albums released by artists.",
        columns=[
            ColumnDefinition("AlbumId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("Title", String(160), nullable=False),
            ColumnDefinition("ArtistId", Integer, nullable=False, foreign_key="Artist.ArtistId"),
        ],
    ),
    TableDefinition(
        name="Employee",
        description="Employees who support customers and manage other employees.",
        columns=[
            ColumnDefinition("EmployeeId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("LastName", String(20), nullable=False),
            ColumnDefinition("FirstName", String(20), nullable=False),
            ColumnDefinition("Title", String(30)),
            ColumnDefinition("ReportsTo", Integer, foreign_key="Employee.EmployeeId"),
            ColumnDefinition("BirthDate", DateTime),
            ColumnDefinition("HireDate", DateTime),
            ColumnDefinition("Address", String(70)),
            ColumnDefinition("City", String(40)),
            ColumnDefinition("State", String(40)),
            ColumnDefinition("Country", String(40)),
            ColumnDefinition("PostalCode", String(10)),
            ColumnDefinition("Phone", String(24)),
            ColumnDefinition("Fax", String(24)),
            ColumnDefinition("Email", String(60)),
        ],
    ),
    TableDefinition(
        name="Customer",
        description="Customers who purchase music and are assigned support reps.",
        columns=[
            ColumnDefinition("CustomerId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("FirstName", String(40), nullable=False),
            ColumnDefinition("LastName", String(20), nullable=False),
            ColumnDefinition("Company", String(80)),
            ColumnDefinition("Address", String(70)),
            ColumnDefinition("City", String(40)),
            ColumnDefinition("State", String(40)),
            ColumnDefinition("Country", String(40)),
            ColumnDefinition("PostalCode", String(10)),
            ColumnDefinition("Phone", String(24)),
            ColumnDefinition("Fax", String(24)),
            ColumnDefinition("Email", String(60), nullable=False),
            ColumnDefinition("SupportRepId", Integer, foreign_key="Employee.EmployeeId"),
        ],
        business_notes=["Join to Invoice for spend analysis and to Employee for account ownership."],
    ),
    TableDefinition(
        name="Genre",
        description="Track genre lookup table.",
        columns=[
            ColumnDefinition("GenreId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("Name", String(120)),
        ],
    ),
    TableDefinition(
        name="MediaType",
        description="Track media format lookup table.",
        columns=[
            ColumnDefinition("MediaTypeId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("Name", String(120)),
        ],
    ),
    TableDefinition(
        name="Playlist",
        description="Named playlists created in the catalog.",
        columns=[
            ColumnDefinition("PlaylistId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("Name", String(120)),
        ],
    ),
    TableDefinition(
        name="Track",
        description="Music track catalog with album, genre, media type, and pricing metadata.",
        columns=[
            ColumnDefinition("TrackId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("Name", String(200), nullable=False),
            ColumnDefinition("AlbumId", Integer, foreign_key="Album.AlbumId"),
            ColumnDefinition("MediaTypeId", Integer, nullable=False, foreign_key="MediaType.MediaTypeId"),
            ColumnDefinition("GenreId", Integer, foreign_key="Genre.GenreId"),
            ColumnDefinition("Composer", String(220)),
            ColumnDefinition("Milliseconds", Integer, nullable=False),
            ColumnDefinition("Bytes", Integer),
            ColumnDefinition("UnitPrice", Numeric(10, 2), nullable=False),
        ],
        business_notes=["Join to InvoiceLine for sales and to Album/Artist for artist performance."],
    ),
    TableDefinition(
        name="Invoice",
        description="Customer invoices with billing geography and order totals.",
        columns=[
            ColumnDefinition("InvoiceId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("CustomerId", Integer, nullable=False, foreign_key="Customer.CustomerId"),
            ColumnDefinition("InvoiceDate", DateTime, nullable=False),
            ColumnDefinition("BillingAddress", String(70)),
            ColumnDefinition("BillingCity", String(40)),
            ColumnDefinition("BillingState", String(40)),
            ColumnDefinition("BillingCountry", String(40)),
            ColumnDefinition("BillingPostalCode", String(10)),
            ColumnDefinition("Total", Numeric(10, 2), nullable=False),
        ],
        business_notes=["Use BillingCountry and Total for revenue by geography."],
    ),
    TableDefinition(
        name="InvoiceLine",
        description="Line-item details for each invoice and purchased track.",
        columns=[
            ColumnDefinition("InvoiceLineId", Integer, nullable=False, primary_key=True),
            ColumnDefinition("InvoiceId", Integer, nullable=False, foreign_key="Invoice.InvoiceId"),
            ColumnDefinition("TrackId", Integer, nullable=False, foreign_key="Track.TrackId"),
            ColumnDefinition("UnitPrice", Numeric(10, 2), nullable=False),
            ColumnDefinition("Quantity", Integer, nullable=False),
        ],
        business_notes=["Multiply UnitPrice by Quantity for revenue at track, album, artist, or genre level."],
    ),
    TableDefinition(
        name="PlaylistTrack",
        description="Bridge table mapping tracks into playlists.",
        columns=[
            ColumnDefinition("PlaylistId", Integer, nullable=False, primary_key=True, foreign_key="Playlist.PlaylistId"),
            ColumnDefinition("TrackId", Integer, nullable=False, primary_key=True, foreign_key="Track.TrackId"),
        ],
    ),
]


def build_metadata() -> MetaData:
    """Create SQLAlchemy metadata that includes keys and foreign keys."""

    metadata = MetaData()
    for table_definition in CHINOOK_TABLES:
        columns: list[Column] = []
        for column in table_definition.columns:
            args = [ForeignKey(column.foreign_key)] if column.foreign_key else []
            columns.append(
                Column(
                    column.name,
                    column.type_,
                    *args,
                    nullable=column.nullable,
                    primary_key=column.primary_key,
                )
            )
        Table(table_definition.name, metadata, *columns)
    return metadata
