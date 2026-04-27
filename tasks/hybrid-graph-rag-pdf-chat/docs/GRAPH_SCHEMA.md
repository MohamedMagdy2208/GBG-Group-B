# Neo4j Graph Schema

This MVP uses Neo4j for structured graph evidence and ChromaDB for vector search. The graph stores documents, chunks, normalized entities, and typed evidence relationships extracted from the PDF.

## Nodes

`Document`

- `id`: stable document ID
- `source_pdf`: PDF file name
- `title`: paper title
- `authors`: author list
- `page_count`: number of pages
- `metadata`: JSON string from PDF metadata
- `ingested_at`, `updated_at`: ISO timestamps

`Chunk`

- `id`: stable chunk ID
- `document_id`: parent document ID
- `source_pdf`: PDF file name
- `title`: paper title
- `text`: chunk text
- `page_numbers`: source pages
- `chunk_index`, `char_count`, `token_estimate`: retrieval/debug metadata

`Entity`

Every extracted entity gets the shared `Entity` label and one concept label:

- `Concept`
- `Actor`
- `Technology`
- `Outcome`
- `Risk`
- `Study`
- `Method`
- `Metric`

Properties:

- `id`: stable ID based on normalized name, independent of extracted type
- `name`: display name
- `normalized_name`: lowercase dedupe/search key
- `type`: selected concept type
- `source_pdf`: originating PDF
- `page_numbers`: pages where observed
- `description`: short grounded description
- `aliases`: alternate names
- `stats`: JSON string for percentages/counts/measurements
- `confidence`: extraction confidence
- `evidence_chunk_ids`: chunk IDs supporting the entity

## Relationships

Document provenance:

- `(Document)-[:HAS_CHUNK]->(Chunk)`
- `(Entity)-[:MENTIONED_IN]->(Chunk)`

Extracted semantic relationships:

- `IMPROVES`
- `INCREASES`
- `CAUSES`
- `RAISES`
- `USES`
- `INCLUDES`
- `STUDIES`
- `IDENTIFIES`
- `REPORTS`
- `RECOMMENDS`
- `ENABLES`

Relationship properties:

- `id`: stable relationship ID
- `source_pdf`: originating PDF
- `page_numbers`: evidence pages
- `evidence`: short supporting phrase
- `evidence_chunk_id`: source chunk
- `properties`: JSON string for optional details
- `confidence`: extraction confidence
- `created_at`, `updated_at`: ISO timestamps

## Applying The Schema

The schema is defined in `scripts/neo4j_schema.cypher` and applied with:

```bash
python scripts/init_neo4j.py
```

To inspect the schema without connecting:

```bash
python scripts/init_neo4j.py --print-schema
```

