"""Generate retrieval documents from database schema and curated examples."""

from __future__ import annotations

from textwrap import dedent

from src.database.schema import CHINOOK_TABLES
from src.utils.types import RetrievalDocument


EXAMPLE_QUERIES: list[tuple[str, str]] = [
    (
        "Top countries by sales",
        dedent(
            """
            SELECT i."BillingCountry", ROUND(SUM(il."UnitPrice" * il."Quantity")::numeric, 2) AS revenue
            FROM "InvoiceLine" il
            JOIN "Invoice" i ON i."InvoiceId" = il."InvoiceId"
            GROUP BY i."BillingCountry"
            ORDER BY revenue DESC
            LIMIT 5
            """
        ).strip(),
    ),
    (
        "Top customers by revenue",
        dedent(
            """
            SELECT c."CustomerId", c."FirstName", c."LastName",
                   ROUND(SUM(i."Total")::numeric, 2) AS revenue
            FROM "Customer" c
            JOIN "Invoice" i ON i."CustomerId" = c."CustomerId"
            GROUP BY c."CustomerId", c."FirstName", c."LastName"
            ORDER BY revenue DESC
            LIMIT 10
            """
        ).strip(),
    ),
    (
        "Most purchased genres",
        dedent(
            """
            SELECT g."Name" AS genre, SUM(il."Quantity") AS purchases
            FROM "InvoiceLine" il
            JOIN "Track" t ON t."TrackId" = il."TrackId"
            JOIN "Genre" g ON g."GenreId" = t."GenreId"
            GROUP BY g."Name"
            ORDER BY purchases DESC
            LIMIT 10
            """
        ).strip(),
    ),
    (
        "Top artists by revenue",
        dedent(
            """
            SELECT ar."Name" AS artist_name,
                   ROUND(SUM(il."UnitPrice" * il."Quantity")::numeric, 2) AS revenue
            FROM "InvoiceLine" il
            JOIN "Track" t ON t."TrackId" = il."TrackId"
            JOIN "Album" al ON al."AlbumId" = t."AlbumId"
            JOIN "Artist" ar ON ar."ArtistId" = al."ArtistId"
            GROUP BY ar."Name"
            ORDER BY revenue DESC
            LIMIT 10
            """
        ).strip(),
    ),
    (
        "Tracks in a playlist",
        dedent(
            """
            SELECT p."Name" AS playlist_name, t."Name" AS track_name
            FROM "PlaylistTrack" pt
            JOIN "Playlist" p ON p."PlaylistId" = pt."PlaylistId"
            JOIN "Track" t ON t."TrackId" = pt."TrackId"
            WHERE pt."PlaylistId" = 1
            ORDER BY t."Name"
            LIMIT 10
            """
        ).strip(),
    ),
    (
        "Sales by year",
        dedent(
            """
            SELECT EXTRACT(YEAR FROM i."InvoiceDate") AS sales_year,
                   ROUND(SUM(i."Total")::numeric, 2) AS revenue
            FROM "Invoice" i
            GROUP BY sales_year
            ORDER BY sales_year
            """
        ).strip(),
    ),
    (
        "Revenue by support representative",
        dedent(
            """
            SELECT e."EmployeeId", e."FirstName", e."LastName",
                   ROUND(SUM(i."Total")::numeric, 2) AS revenue
            FROM "Employee" e
            JOIN "Customer" c ON c."SupportRepId" = e."EmployeeId"
            JOIN "Invoice" i ON i."CustomerId" = c."CustomerId"
            GROUP BY e."EmployeeId", e."FirstName", e."LastName"
            ORDER BY revenue DESC
            """
        ).strip(),
    ),
    (
        "Average track length by genre",
        dedent(
            """
            SELECT g."Name" AS genre,
                   ROUND(AVG(t."Milliseconds") / 1000.0, 2) AS avg_seconds
            FROM "Track" t
            JOIN "Genre" g ON g."GenreId" = t."GenreId"
            GROUP BY g."Name"
            ORDER BY avg_seconds DESC
            LIMIT 10
            """
        ).strip(),
    ),
    (
        "Customers by country",
        dedent(
            """
            SELECT c."Country", COUNT(*) AS customer_count
            FROM "Customer" c
            GROUP BY c."Country"
            ORDER BY customer_count DESC, c."Country"
            """
        ).strip(),
    ),
]


def build_schema_documents(schema_snapshot: list[dict]) -> list[RetrievalDocument]:
    """Convert live schema metadata into retrieval-ready documents."""

    documents: list[RetrievalDocument] = []
    definitions = {table.name: table for table in CHINOOK_TABLES}

    for table in schema_snapshot:
        table_name = table["table"]
        definition = definitions.get(table_name)
        column_lines = [
            f'- {column["name"]} ({column["type"]}, nullable={column["nullable"]})'
            for column in table["columns"]
        ]
        relationship_lines = [
            f'- {",".join(fk["constrained_columns"])} -> {fk["referred_table"]}.{",".join(fk["referred_columns"])}'
            for fk in table["foreign_keys"]
        ] or ["- No foreign keys detected."]

        notes = definition.business_notes if definition else []
        doc_text = "\n".join(
            [
                f"Table: {table_name}",
                f"Purpose: {(definition.description if definition else 'Business table in the music store database.')}",
                "Columns:",
                *column_lines,
                "Relationships:",
                *relationship_lines,
                *(["Business notes:"] + [f"- {note}" for note in notes] if notes else []),
            ]
        )
        documents.append(
            RetrievalDocument(
                doc_id=f"schema::{table_name}",
                title=f"{table_name} schema",
                kind="schema",
                text=doc_text,
                metadata={"table": table_name},
            )
        )
    return documents


def build_example_documents() -> list[RetrievalDocument]:
    """Return curated example question-to-SQL retrieval documents."""

    documents: list[RetrievalDocument] = []
    for index, (title, sql) in enumerate(EXAMPLE_QUERIES, start=1):
        documents.append(
            RetrievalDocument(
                doc_id=f"example::{index}",
                title=title,
                kind="example",
                text=f"Business question: {title}\nHelpful SQL pattern:\n{sql}",
                metadata={"example_sql": sql},
            )
        )
    return documents


def build_all_documents(schema_snapshot: list[dict]) -> list[RetrievalDocument]:
    """Build the full retrieval corpus used by the app."""

    return [*build_schema_documents(schema_snapshot), *build_example_documents()]
