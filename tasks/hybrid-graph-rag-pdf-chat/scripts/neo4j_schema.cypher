// Core uniqueness constraints.
CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// Lookup indexes used by ingestion, inspection, and hybrid retrieval.
CREATE INDEX document_source_pdf_index IF NOT EXISTS
FOR (d:Document) ON (d.source_pdf);

CREATE INDEX chunk_document_id_index IF NOT EXISTS
FOR (c:Chunk) ON (c.document_id);

CREATE INDEX chunk_source_pdf_index IF NOT EXISTS
FOR (c:Chunk) ON (c.source_pdf);

CREATE INDEX entity_name_index IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE INDEX entity_normalized_name_index IF NOT EXISTS
FOR (e:Entity) ON (e.normalized_name);

CREATE INDEX entity_type_index IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX entity_source_pdf_index IF NOT EXISTS
FOR (e:Entity) ON (e.source_pdf);

CREATE FULLTEXT INDEX entity_fulltext_index IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.normalized_name, e.description, e.aliases];

// Relationship indexes keep evidence lookup fast without requiring relationship
// uniqueness constraints, which vary more across Neo4j editions/versions.
CREATE INDEX improves_source_pdf_index IF NOT EXISTS
FOR ()-[r:IMPROVES]-() ON (r.source_pdf);

CREATE INDEX increases_source_pdf_index IF NOT EXISTS
FOR ()-[r:INCREASES]-() ON (r.source_pdf);

CREATE INDEX causes_source_pdf_index IF NOT EXISTS
FOR ()-[r:CAUSES]-() ON (r.source_pdf);

CREATE INDEX raises_source_pdf_index IF NOT EXISTS
FOR ()-[r:RAISES]-() ON (r.source_pdf);

CREATE INDEX uses_source_pdf_index IF NOT EXISTS
FOR ()-[r:USES]-() ON (r.source_pdf);

CREATE INDEX includes_source_pdf_index IF NOT EXISTS
FOR ()-[r:INCLUDES]-() ON (r.source_pdf);

CREATE INDEX studies_source_pdf_index IF NOT EXISTS
FOR ()-[r:STUDIES]-() ON (r.source_pdf);

CREATE INDEX identifies_source_pdf_index IF NOT EXISTS
FOR ()-[r:IDENTIFIES]-() ON (r.source_pdf);

CREATE INDEX reports_source_pdf_index IF NOT EXISTS
FOR ()-[r:REPORTS]-() ON (r.source_pdf);

CREATE INDEX recommends_source_pdf_index IF NOT EXISTS
FOR ()-[r:RECOMMENDS]-() ON (r.source_pdf);

CREATE INDEX enables_source_pdf_index IF NOT EXISTS
FOR ()-[r:ENABLES]-() ON (r.source_pdf);

