# Understanding the Folio Equity Research Project

A complete beginner guide to the application, its data, its AI, and its engineering decisions

Prepared for a colleague learning the project from the beginning

## How to read this guide

Folio is a website that helps a person search company financial reports and, when AI is configured, receive an answer linked to supporting passages. It is a small research application, not a stock trading system, a live stock-price service, or an automatically verified accountant.

Read Sections 1 through 7 first to understand the basic idea. Sections 8 through 18 explain the database and the two complete data flows. Sections 19 onward cover financial examples, limitations, setup, troubleshooting, and interview questions. You do not need previous knowledge of AI or databases. New technical terms are explained before they are used.

The most important fact is this: the application keeps original evidence and uses AI to help find and explain it. A vector is a search representation of evidence. It does not replace that evidence.

## 1 The problem we are solving

Imagine that you want to understand Apple. You download a long annual report and a quarterly earnings statement. Somewhere in those documents are revenue figures, expense descriptions, business risks, and explanations of what changed. You could read every page manually, but finding the relevant passages repeatedly takes time.

You might ask, “What was Apple's Q4 income?” A useful application must identify the company, decide which fiscal quarter and year you mean, find the right table, distinguish revenue from net income, read the correct column, and show where the number came from.

Folio organizes those documents into a searchable library. It can return source excerpts directly. With an AI provider enabled, it can also compose an explanation from retrieved passages and attach source references.

The intended result is faster access to evidence. It is not permission to skip reading the evidence when the answer matters.

### A familiar analogy

Think of the application as a small library. The reports are books. Page numbers and document titles are the catalog. A search system finds relevant pages. An AI writing assistant reads the selected passages and writes an answer. The answer includes references so the reader can return to the books.

The writing assistant is not the library, and the catalog is not the books. In the same way, the language model, vector search, database, and PDF files have different jobs.

## 2 What the reader sees on the website

The interface has three main pages.

| Page | What it is for |
|---|---|
| Search | Select a company, optionally set year and period filters, and ask a question. View an AI answer or retrieved source excerpts. |
| Sources | Browse and search the financial reports. Check document identity and annual or quarterly coverage. Open the saved original or publisher source. |
| Architecture | See how documents are processed and how a question becomes an answer. Inspect configured models, retrieval settings, and library counts. |

The local owner version also supports adding companies, uploading reports, saved research, a financial snapshot, metric extraction candidates, and Markdown export. These functions do not all come from the same data pipeline. For example, financial snapshots are obtained from SEC company facts, while research answers use retrieved report passages.

The architecture page reports the current configuration. If embeddings are disabled, the application is doing source search, not full semantic RAG. If answer generation is disabled, it is returning evidence rather than having a language model write an explanation.

### Example interaction

1. Select AAPL, the ticker symbol for Apple.
2. Ask “q4 income.”
3. The application checks which Q4 reports are available for Apple.
4. It discloses its chosen year and its interpretation of “income.”
5. It retrieves passages, optionally generates an answer, and provides source buttons.
6. Open a source button to inspect the excerpt and report page.

Selecting a company is important. The application does not perform unrestricted cross-company analysis just because a company name appears in the question.

## 3 Basic computer terms used in this project

**Frontend** means the part shown in the browser: headings, forms, buttons, cards, and diagrams. This project uses HTML for page structure, CSS for appearance, and JavaScript for browser behavior. It is not a React or Next.js application.

**Backend** means the Python program that receives requests, accesses the database, processes documents, and calls optional AI services. FastAPI provides the web API, and Uvicorn runs the Python web server.

**Server** means a running program that listens for requests and returns responses. A server can run on your laptop. It does not have to be a rented cloud machine.

**API** means an agreed interface through which programs communicate. The browser can request a document list from the backend API. Separately, the backend can call an external OpenAI API. These are two different connections.

**Endpoint** is a particular API address and operation. For example, GET /api/library reads the library, while POST /api/research submits a question. GET normally reads information; POST commonly submits information or starts work.

**JSON** is a text format for exchanging structured information. A small request can look like this:

```json
{"ticker": "AAPL", "question": "q4 income", "answer_mode": "ai"}
```

**Database** means a system for storing and querying records. **Table** means a collection of records with named columns. A row is one record. **Primary key** means the identifier that uniquely selects a row. **Foreign key** means a link from a row to a related row in another table.

**Persistence** means information remains after the program stops. **RAM** is temporary working memory; disk stores files persistently. A cloud database still uses physical computers, RAM, and disks, but a provider operates them.

## 4 What local means and what GitHub does

The address 127.0.0.1 means the computer on which you are opening the browser. Port 8080 identifies the listening application on that computer. The command below starts Folio locally:

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

After the server starts, open http://127.0.0.1:8080 on the same computer. Keep the server process running. Opening this address on another laptop does not reach your laptop; it refers to that other laptop. That person must start their own application, or use a separately hosted shared service.

GitHub stores source code and version history. Reading the public repository does not start the Python application, run a database, download reports, or grant access to the author's API account.

Public source code and a public running service are separate decisions. Our public repository contains a local version with setup instructions. A separate private repository was used for an earlier Render deployment. Making a repository private does not put a login in front of a website already deployed from it.

### Local does not always mean offline

The Python server can run locally while still contacting OpenAI for AI processing or Supabase for database storage. A configuration using SQLite and local models can keep those functions on the computer after model files are downloaded. Downloading financial reports still needs an internet connection.

## 5 The versions that exist

This distinction prevents a great deal of confusion.

| Version or mode | Data storage | Search and answers | Hosting relationship |
|---|---|---|---|
| Public repository default | Local SQLite | Keyword source search; no embeddings or generated answers by default | Runs on the reader's computer. No Render configuration or demo URL is included. |
| Local application with OpenAI enabled | SQLite or the user's PostgreSQL database | OpenAI embeddings and optional generated answers | Python stays local; selected text is sent to OpenAI. |
| Local application with local models | SQLite or configured PostgreSQL | Optional local embeddings and Ollama answers | Models require separate installation, downloads, and memory. |
| Previously configured private deployment | Supabase PostgreSQL with pgvector | OpenAI embeddings and generated answers | Separate Render web service with demo restrictions. |

The public repository is at https://github.com/tvivekanandareddy/folio-equity-research-local. It contains no working account credentials and no preloaded personal database. A fresh clone therefore does not automatically contain all reports, vectors, or saved questions from the author's workspace.

The earlier configured corpus had 8 companies, 10 reports, 2,756 chunks and cached vectors, and 653 extracted page or text-section records. These are recorded setup counts, not a guarantee about a fresh installation or current service availability. Microsoft HTML-derived text is stored as a text section rather than hundreds of original PDF pages.

On the last connection check on November 10, 2026, the earlier hosted application responded but its database health check failed. The reason had not been confirmed from the database dashboard. This guide explains the implementation; it does not claim that deployment is currently healthy.

## 6 The technology choices in one place

| Component | Tool actually used | Job |
|---|---|---|
| Browser interface | HTML, CSS, JavaScript | Display the application and send questions. |
| Backend | Python with FastAPI | Coordinate data processing, search, and responses. |
| Web server | Uvicorn | Run the FastAPI application. |
| PDF extraction | pypdf | Read text from text-based PDF pages. |
| HTML extraction for the report downloader | BeautifulSoup | Turn selected investor report HTML into readable text. |
| Local database | SQLite | Store the library and history without a separate database server. |
| Optional online database | Supabase PostgreSQL | Store related records in a managed database. |
| PostgreSQL vector support | pgvector extension | Store vectors and perform vector distance searches. |
| Configured embedding model | OpenAI text-embedding-3-small | Convert passages and questions into 1,536-number vectors. |
| Configured answer model | OpenAI gpt-5-mini | Generate an answer from selected evidence. |
| Database client | psycopg | Connect Python to PostgreSQL. |
| HTTP client | httpx | Download documents and call configured APIs. |
| Vector arithmetic | NumPy | Compute similarity in the current small-corpus implementation. |

The code coordinates these operations directly. It does not require LangChain or LlamaIndex. It does not use Vertex AI, Cloud Run, Firestore, Pinecone, Chroma, or Qdrant in the configured research path.

Vertex AI and Google Cloud were considered in the original project idea. The implementation changed. An interview explanation should name the tools that were actually used, rather than repeat the earlier proposed stack.

## 7 What RAG means

RAG stands for retrieval-augmented generation.

**Retrieval** means finding relevant passages in the document collection. **Augmented** means adding those passages to the information supplied to a language model. **Generation** means the model writes an answer using that supplied material.

The question and the selected passages together become part of the model's input. The model does not receive the whole library on every question. It receives a small set of relevant excerpts, usually up to five in this implementation.

Without retrieval, a model may answer from its general learned patterns and miss your particular filing. With retrieval, we can supply the exact report evidence and preserve its source location. This improves grounding but does not guarantee truth: the wrong passage can be retrieved, a table can be misread, or the model can overstate what the evidence says.

### RAG is not training a new model

This application does not train or fine-tune a language model on the reports. It builds a searchable collection and supplies retrieved text at question time. Updating the collection changes what evidence is available without retraining the answer model.

An embedding call is also not model training. It runs an already trained model to produce a representation of the input text.

With AI disabled, Folio remains a document search application. Calling that mode a complete generated-answer RAG system would be inaccurate because the generation step is absent.

## 8 What data the project stores

The project stores more than vectors. It keeps document identity, original text, locations, source links, company information, and research results.

| Table | What a row represents | Why it is needed |
|---|---|---|
| companies | A company and its stored JSON payload | Company identity and financial snapshot data. |
| documents | One ingested report | Title, ticker, year, period, hash, origin, publisher URL, and saved-file location. |
| pages | One extracted PDF page or text section | Preserve readable evidence and page identity. |
| chunks | One searchable passage | Store the text segment linked to its document and page. |
| document_periods | One reviewed period covered by a document | A release can cover both Q4 and FY. |
| embeddings | A chunk's vector and embedding model | Support semantic similarity search. |
| research | A saved question, answer, and source snapshot | Restore history and export previous work. |
| metric_candidates | A proposed extracted financial observation | Keep values requiring human review separately. |

The public local version has these eight application tables. SQLite also has FTS5 search structures. The separate hosted demo version adds a ninth table, demo_usage, for request allowances.

Some payloads are JSON serialized into TEXT columns. The application is not using a fully normalized financial accounting warehouse. Although PostgreSQL supports JSON and JSONB, our existing payload columns are TEXT. Those details matter when explaining the actual schema.

Original PDFs are saved as files under data/documents. Download scripts also use data/reports. The database stores paths and extracted text; it does not automatically upload the original PDFs into Supabase Storage.

## 9 Why SQL can store unstructured documents

Structured data has named fields with predictable meanings, such as ticker, fiscal year, and page number. Unstructured data includes free-form paragraphs, letters, risk descriptions, and management discussion. A financial report contains both, often mixed on the same page.

A SQL database can store a paragraph in a TEXT column. It does not require us to turn every sentence into an accounting row. For example, a chunk can contain a full paragraph about supply-chain risks while nearby columns store AAPL, 2024, and page 17.

Those columns describe the paragraph; they do not force the paragraph itself into a rigid financial table. We can search the text semantically while using SQL to filter by company and period and join back to its source.

### A concrete row

The following is a simplified teaching example, not a copied production row:

| id | document_id | ticker | page_number | text |
|---|---|---|---|---|
| chunk_demo_1 | report_demo_1 | AAPL | 17 | The company describes supply constraints and dependence on third-party manufacturers. |

The text can be several sentences long. It remains understandable English. A separate embeddings row links chunk_demo_1 to a vector. Neither row needs a dedicated column for every idea in the paragraph.

Therefore, “the documents contain unstructured text” does not imply “we must use a NoSQL database.” Storage format, relationships, and search capability are different concerns.

## 10 Why we chose PostgreSQL and SQLite

For the configured shared database, PostgreSQL plus pgvector keeps source relationships, text, and vectors in one database. A passage belongs to a page and report. A saved result refers to evidence. SQL joins and foreign keys make those relationships explicit.

Transactions help related writes succeed or fail together. For example, document metadata, page records, and chunk records are inserted in one database transaction. PostgreSQL also supports full-text search, so keyword and vector retrieval can share the same store.

Supabase is the managed service used to operate PostgreSQL for the online configuration. It is not a separate vector database product. pgvector is an extension installed inside PostgreSQL. PostgreSQL is the database engine; Supabase operates it; pgvector adds vector storage and distance operators.

For the local version, SQLite reduces setup. It is a library that reads and writes a database file without a separate database server. That fits a single-person learning project and makes tests easy to isolate. [S3]

SQLite in this project is not running pgvector. It stores vectors as JSON text and compares them in Python. It uses FTS5 for keyword search. PostgreSQL stores vectors in the pgvector type and can search them in the database.

### The actual decision

We chose SQL because the project combines related records, source traceability, optional financial observations, text, and vector search. We did not choose it because SQL is always faster, because NoSQL cannot store financial data, or because every RAG application requires relational tables.

For a one-person local clone, SQLite is the lower-setup choice. For the configured online persistence, PostgreSQL plus pgvector avoids introducing a second database just to store vectors.

## 11 Could we use NoSQL or a different vector store

Yes. NoSQL systems can store documents, metadata, financial values, and source references. Some also support vector search and transactions. SQL and NoSQL are not a simple contest between “structured” and “AI-friendly.” Their capabilities overlap.

The question is which combination of relationships, filters, operations, deployment effort, and scale fits this application.

| Option | Why it is reasonable | Why we did not choose it here |
|---|---|---|
| PostgreSQL with pgvector | Related records, transactions, SQL filters, text search, and vectors together | Our selected online store; still needs a database service and careful indexing as scale grows. |
| SQLite with Python similarity | Minimal local setup and one main database file | Our local default; current vector comparisons read candidates into Python. |
| Chroma | Retrieval-focused storage for documents, embeddings, and metadata | Another valid prototype path, but our relational source/history workflow already fits SQL. [S5] |
| Qdrant | A specialized vector system with payload filtering and hybrid-query capabilities | Useful when retrieval requirements justify a separate service; not required by this corpus. [S6] |
| FAISS | A library for efficient vector similarity search | It is not a full application database; we would still need to manage text, metadata, persistence, and relationships around it. [S7] |
| A document-oriented NoSQL database | Flexible document records and, depending on product, vector search | Valid alternative; we would redesign source links, query paths, and integrity checks rather than simply swap a connection string. |

Specialized vector stores can store text and metadata too. It would be wrong to claim that they store only numbers. We selected one SQL database for convenience and consistency, not because those alternatives are incapable.

Even a simple user question needs the correct company, period, unit, and source. Query simplicity alone does not decide the database. Scale and operational requirements can change the decision later.

## 12 What an embedding vector looks like

An embedding is an ordered list of numbers produced by an embedding model. It is a representation that helps compare text by learned patterns of meaning.

For teaching, imagine this short vector:

```text
Passage text: Revenue increased as subscription sales grew.
Illustrative vector: [0.12, -0.08, 0.44, 0.03]
```

Those four numbers are invented for illustration. Our configured OpenAI text-embedding-3-small model normally returns 1,536 numbers per passage or question. We do not set the dimensions parameter to shorten it. OpenAI documents that default dimension count. [S1]

A dimension is one coordinate in that numerical representation. Do not say “dimension 1 means revenue” or “dimension 2 means profit.” The coordinates are learned jointly and generally do not have simple human-readable labels.

Text with similar meaning often has similar vectors, even when the words differ. For example, “What drove sales growth?” may match a passage about increased revenue. This is useful, but financial terms such as revenue, operating income, net income, and cash flow remain different. Similarity is not an accounting validation rule.

### Are we storing numbers and searching numbers

For semantic retrieval, yes: we compare the question's vector with passage vectors. After that, we use the matching chunk IDs to retrieve readable text and source metadata. The answer model reads that text. It does not receive an unexplained vector and reconstruct the report from it.

Embeddings are not a secure encryption of the document. Keep confidential text and its representations protected. This project uses publicly available company reports, but a private upload would still require an appropriate data-handling decision.

## 13 How document embeddings are created and stored

The configured embedding model is text-embedding-3-small. The answer-writing model is gpt-5-mini. They perform different tasks and need not be the same model.

For persisted chunks, the indexing function checks whether each chunk already has an embedding for the configured model. Missing chunks are sent in batches. The OpenAI adapter divides embedding inputs into batches of up to 64. Responses are validated before vectors are saved.

The embeddings table connects chunk_id, model, and embedding. In PostgreSQL, embedding uses the extensions.vector type. In SQLite, embedding is a JSON array serialized into a TEXT column.

The current table's primary key is chunk_id, not the pair of chunk_id and model. This means a chunk has one stored embedding row at a time. Switching the configured model can replace that row. It is not a multi-model vector archive.

The code checks model identity when reading vectors. Vectors from different models must not be mixed just because their dimension counts happen to match. Different models create different coordinate spaces.

### When embedding calls happen

In the local owner version, an indexing script can precompute embeddings, or a research request can index missing persisted chunks. Completed batches remain saved if a later batch fails. Existing embeddings are reused when chunk and model match.

Each new question is also embedded for semantic retrieval. Question embeddings are not persisted in a dedicated query cache. We are not re-embedding the entire library for every question when its vectors are already present.

The separate hosted demo blocks automatic document indexing. That protection is specific to that deployed variant, not the public local repository.

## 14 The complete document write path

This is everything that happens when a real document enters the library.

1. **Obtain the file.** A user uploads a PDF/TXT file, or the report downloader obtains a configured issuer document. The Microsoft annual report begins as HTML and is converted to text.
2. **Assign metadata.** The application receives the ticker, optional fiscal year, period, title, origin, and publisher URL. Upload metadata comes from the user; it is not automatically proven correct.
3. **Check the input.** The ingestion code accepts text-based PDF or UTF-8 TXT. It enforces file and extracted-text limits and rejects files with too little usable text.
4. **Extract pages.** pypdf extracts PDF text page by page. A TXT file is treated as one text section. Physical PDF page numbers are preserved.
5. **Hash the file.** SHA-256 gives a content fingerprint. The ticker plus file hash determines the document ID, allowing identical company/file uploads to be recognized.
6. **Split text into chunks.** Each page is divided into passages of approximately 1,100 characters with about 150 characters of overlap. Splitting favors a word boundary. These sizes are characters, not tokens.
7. **Save the original.** A content-derived filename is written under data/documents using a temporary file and atomic rename.
8. **Write database records.** One transaction stores the document, extracted pages, and chunks. SQLite also receives its FTS5 records. Duplicate document IDs do not create another set of chunks.
9. **Record reviewed coverage.** A separate setup function can add FY and Q4 coverage for documents that genuinely include both periods.
10. **Optionally index vectors.** Embeddings are a subsequent operation, not part of the same all-or-nothing transaction as original document ingestion.

A database failure can leave an unused saved file because filesystem writes and database commits are not one distributed transaction. A later embedding failure can leave valid text searchable by keywords but not yet fully indexed semantically. These are distinct failure cases.

## 15 Why we split text into overlapping chunks

Searching an entire report as one object is often too broad. A report may contain both product strategy and income statements. A small question benefits from a focused passage about its subject.

Chunks make the units of retrieval smaller. The answer model receives selected passages instead of every page. This controls the amount of input and makes it easier to connect an answer to its location.

However, splitting can separate related material. A sentence can cross a boundary. A table row may be separated from its date columns. Overlap repeats some text between adjacent chunks to reduce abrupt loss of context.

The implemented splitter works inside each page. It does not merge a sentence across two different PDF pages. Therefore, overlap is helpful but does not solve every layout problem.

For quarterly retrieval, the code can prepend the first 500 characters of the source page as a page header. This helps carry units and date columns alongside later table rows. It is a heuristic, not a complete financial-table parser.

### Why approximately 1100 and 150

These are prototype settings chosen to keep passages reasonably small while preserving some neighboring text. They are not proven universally optimal. A careful evaluation might select different sizes for prose, tables, headings, or different models.

Smaller chunks may improve focus but lose context. Larger chunks preserve more context but may include irrelevant text and increase model input. More overlap creates additional repeated evidence and storage. The current system has no table-specific chunking strategy or learned reranker.

## 16 The complete question read path

This is what happens after you click Search with semantic retrieval and generated answers enabled.

1. The browser sends the question, selected ticker, filters, and answer mode to POST /api/research.
2. FastAPI validates the request. Questions must contain 3 to 2,000 characters; years and period filters are constrained.
3. The backend finds the selected company. It interprets explicit quarter/year language and detects certain conflicts with the selected filters.
4. It loads chunks belonging to the allowed company and report scope. Filtering happens before the result set is selected.
5. Keyword retrieval and lexical scoring create one ranking of those candidate chunks.
6. In semantic mode, the question is embedded with the same embedding model used for report chunks. Local owner mode can index missing document vectors first.
7. Candidate vectors are compared with the question vector. PostgreSQL performs exact pgvector cosine search; the current implementation also reads candidate vectors and computes similarities in Python.
8. The lexical and semantic rankings are combined using reciprocal rank fusion. At most five passages are selected.
9. Quarterly page headers are attached where available. The backend creates numbered source references.
10. In AI answer mode, the question, instructions, and selected passages go to the configured answer model. In excerpt mode, generation is skipped.
11. The backend checks that numeric citation references exist and are within the selected source range. Invalid or missing references cause a fallback to evidence excerpts.
12. The question, answer, scope, sources, and timestamp are saved in research. The browser displays the result and source buttons.

Previous research history is not automatically added to the next model prompt. This is saved research, not a full multi-turn conversational memory system.

## 17 What similarity and hybrid retrieval mean

Cosine similarity compares the directions of vectors. More aligned vectors generally receive a higher similarity. In pgvector, the cosine-distance operator is <=>, and similarity can be computed as one minus that distance.

This is a relevance score, not a probability that a financial statement is correct. A passage can be semantically close yet contain the wrong year or the wrong metric. That is why metadata filters and source inspection matter.

For a tiny numerical example, use a question vector [1, 0] and two passage vectors [0.8, 0.6] and [0, 1]. Each has length one. The first passage has cosine similarity 0.8 with the question; the second has similarity 0. The first is closer by this numerical rule. These are teaching vectors, not actual financial embeddings. Real model coordinates generally cannot be explained individually this way.

The application also uses keyword evidence. Exact terms, tickers, accounting labels, and numbers can be valuable even when semantic similarity is imperfect.

In PostgreSQL, full-text search uses text-search functions and ranks matches. SQLite uses FTS5. The application also computes a BM25-style lexical score over candidate text and combines matching IDs with database keyword hits. Its tokenizer and stop words are largely English-oriented.

### How the two rankings are combined

Reciprocal rank fusion rewards a passage for appearing high in either ranking. A contribution is one divided by 60 plus the passage's one-based rank. Contributions are added across the lexical and semantic lists.

A passage ranked near the top of both lists receives two contributions. A passage appearing only in one list receives one. Rank fusion avoids pretending that a keyword score and a cosine score have the same numerical scale.

This is not a separate neural reranker. The system does not currently send the retrieved candidates to a cross-encoder model for a second learned relevance judgment.

There is also no minimum relevance threshold that guarantees every returned passage is useful. An unsupported question can still retrieve superficially related passages; the model must recognize insufficient evidence, and the reader must verify the answer.

## 18 What retrieval k means and what indexes exist

Retrieval k is the maximum number of passages selected for the answer context. Here, the final k is 5. That means up to five passages, not five companies, five whole reports, or five generated answers.

The database keyword candidate limit is normally 30. The PostgreSQL vector candidate call in the retrieval function asks for up to 30 results. Those candidate settings are different from the final five evidence passages. The implementation also computes a semantic ranking over loaded candidate vectors in Python.

The answer context can contain fewer than five passages. It can contain overlapping passages from the same report or page. There is currently no rule limiting selection to a certain number per document, so duplicate-looking source buttons can occur.

### Exact search and approximate search

The configured pgvector path uses exact cosine search. Exact means it compares the relevant vectors without relying on an approximate nearest-neighbor index. It does not mean it always understands the question perfectly. [S2]

HNSW and IVFFlat are examples of approximate vector indexes available in pgvector. They can improve speed at larger scale with tradeoffs and tuning. Our schema does not create either one. [S2]

The schema does include ordinary relational indexes and a PostgreSQL GIN full-text expression index. SQLite creates an FTS5 virtual table. A primary key is also an index, but none of these should be mislabeled as an HNSW vector index.

For a few thousand chunks, exact comparison is a reasonable starting implementation. Reading vectors into Python and duplicating some ranking work would become expensive for a very large library. Performance claims need measurements; no million-document benchmark has been established for this project.

## 19 A complete worked financial example

Consider “Compare Apple's revenue in 2023 and 2024, and show the sources.” A user asking this likely wants annual revenue, not quarterly revenue, and needs values with matching units.

Apple's Q4/FY2024 consolidated statements contain both quarterly and annual columns. On physical PDF page 1, total net sales for the twelve-month columns are USD 383,285 million for FY2023 and USD 391,035 million for FY2024. [S4]

| Item | Value |
|---|---|
| FY2023 annual net sales | USD 383,285 million |
| FY2024 annual net sales | USD 391,035 million |
| Absolute increase | USD 7,750 million |
| Percentage increase | Approximately 2.02 percent |

To calculate the percentage, subtract the previous year from the current year, divide by the previous year, then multiply by 100. The arithmetic uses matching annual columns and units. USD 391,035 million is USD 391.035 billion; it is not USD 391,035 billion.

The correct supporting location is the statement containing those annual columns. The application should attach the report and page reference so the reader can verify it. An annual comparison can be supported by a report containing both years; two separate files are not always necessary.

### What our research endpoint actually does

The endpoint retrieves passages and asks the model to explain them. It does not automatically execute a trusted SQL accounting calculation for every revenue question. A generated comparison still needs its numbers and arithmetic checked. The separate metric-extraction workflow stores review candidates, not a fully accepted financial facts table.

The question resolver detects a single explicit year. When a question contains two years, it does not automatically build a separate query for each year. With no conflicting explicit filter, broader relevant report passages can still include both annual columns. Cross-year source balancing is not guaranteed.

## 20 Why Q4 income needs careful interpretation

Q4 means the fourth fiscal quarter. A fiscal year is a company's reporting year; its ending date need not be December 31. Comparing “2024” across companies without checking fiscal calendars can be misleading.

Revenue is money earned from sales before many costs. Net income is the remaining profit after the applicable expenses and taxes. Operating income and cash flow are different measures again. The application must not silently use these terms interchangeably.

For the short question “q4 income,” the implemented resolver uses the selected company, looks for the latest Q4 year available in that company's library, and discloses that unspecified income is interpreted as GAAP net income. It does not assume the latest calendar year or fetch a new filing automatically.

For Apple fiscal Q4 2024, page 1 of the cited statement reports GAAP net income of USD 14,736 million for the three months ended September 28, 2024. The same table contains an annual net-income figure of USD 93,736 million. These are different period columns and cannot be substituted for one another. [S4]

GAAP means generally accepted accounting principles in this reporting context. Non-GAAP adjusted results may differ and must be labeled rather than substituted silently.

If only an annual report is available for a company, the system should not invent Q4 income from it. The implementation reports missing coverage rather than treating full-year totals as quarter totals. Deriving a quarter as full year minus nine months could be a separate reviewed workflow, but it is not the current default and requires compatible source definitions and periods.

## 21 Seeing real SQL and sample records

SQL is the language used to ask a relational database for records. The following example retrieves Apple passages and their source locations using the actual table structure. It does not extract numeric accounting facts by itself.

```sql
SELECT d.title, c.page_number, c.text, d.source_url
FROM chunks AS c
JOIN documents AS d ON d.id = c.document_id
WHERE c.ticker = 'AAPL'
  AND d.fiscal_year = 2024
ORDER BY c.page_number, c.id
LIMIT 5;
```

JOIN means connect matching records. Here, c.document_id identifies the document to which the chunk belongs. The returned text can be a paragraph or an extracted table fragment. In application code, user inputs are supplied as query parameters rather than pasted into SQL strings.

The PostgreSQL vector-search operation uses the following pattern. The %s symbols are values supplied by the Python database driver, not text the reader should paste into a SQL editor unchanged. The allowed chunk IDs already come from the company/period filtering step.

```sql
SELECT chunk_id,
       1 - (embedding OPERATOR(extensions.<=>)
            %s::extensions.vector) AS score
FROM embeddings
WHERE model = %s AND chunk_id = ANY(%s)
ORDER BY embedding OPERATOR(extensions.<=>)
         %s::extensions.vector
LIMIT %s;
```

The supplied values are the question vector, model name, allowed IDs, the same question vector again, and a candidate limit. The distance operator compares numbers, while the returned chunk ID reconnects the result to readable evidence.

### A tiny connected database example

These identifiers and the short vector below are invented teaching values. The text and vector are deliberately shortened.

| Table | Example record |
|---|---|
| documents | id = report_demo_1; ticker = AAPL; fiscal_year = 2024; title = Example statement |
| pages | id = page_demo_1; document_id = report_demo_1; page_number = 1; text = original extracted page text |
| chunks | id = chunk_demo_1; document_id = report_demo_1; page_number = 1; text = selected passage |
| embeddings | chunk_id = chunk_demo_1; model = configured embedding model; embedding = [0.12, -0.08, 0.44, 0.03] |

The embedding search finds chunk_demo_1. Its link to the chunk yields text. Its link to the document yields the title and publisher URL. The page number takes the reader back to the original physical PDF page. This is why we preserve relationships instead of storing an anonymous vector alone.

## 22 Extracting financial metrics is a separate workflow

“Search for relevant passages” and “create trustworthy financial facts” are different tasks. A nearby sentence might mention a value from another year or use thousands instead of millions.

The metric extraction endpoint selects up to 16 passages using financial-term occurrence scores. It asks the configured answer model for schema-shaped observations containing a metric, year, value, unit, source ID, and supporting quote.

The backend validates the output structure. It requires an allowed source ID, a nonempty supporting quote actually present in the selected source, and a finite numeric value. Valid-looking observations are saved in metric_candidates with status needs_review.

That quote check does not prove that the extracted number, sign, unit, period, or accounting definition is correct. A quote can be present while the model associates it with the wrong column.

The extraction function also constructs some year-over-year comparisons when it finds unique values for matching metric/unit/year groups in the current extraction result, a prior consecutive year, and a nonzero previous value. Conflicting duplicate values are excluded from those comparisons. That logic does not turn the whole database into a verified accounting ledger.

### Where dashboard financial snapshots come from

Company financial snapshots are populated from SEC company facts through the company import path. They are not automatically overwritten by model-extracted metric candidates. The SEC data path selects annual 10-K, full-year facts in USD and computes compatible dashboard comparisons where possible.

For a production financial system, we would want reviewed facts with explicit taxonomy, period dates, fiscal/calendar treatment, currency, units, restatement policy, source provenance, and approval history. Those are future requirements, not claims about the current prototype.

## 23 Citations and what they prove

A citation such as [3] means “look at source number 3 in this response.” The backend gives the model numbered passages and checks that the numbers it cites are valid for that response.

If no numeric citation is present, or a cited number is outside the available source range, the application falls back to retrieved excerpts and displays a warning. This catches a useful class of malformed answers.

However, a valid source number does not prove that the source supports every claim. The system does not run a full claim-by-claim factual verifier, and it does not independently audit all arithmetic. A language model can cite a real passage and still misread it.

Source buttons show the selected excerpt, title, PDF page or text-section location, and links. PDF page numbers are physical positions in the file; they can differ from printed page labels, especially in bundles containing a proxy statement and an annual report.

The publisher URL is stored as metadata. Original-file links in local mode require that the file still exists on that computer. The earlier hosted demo can redirect a missing local original to its stored HTTPS publisher URL. That redirect behavior belongs to the hosted variant.

Source references are useful because a human can inspect the evidence. They are not a guarantee that generated financial analysis is correct.

## 24 Images charts scanned PDFs and tables

The current pipeline extracts text. It does not perform visual chart interpretation, OCR, or automatic image-to-table conversion.

If a PDF page contains real selectable text, pypdf can often extract it. If it contains only a scanned picture of text, extraction may return almost nothing. The application rejects documents with insufficient usable text and explains that scanned reports need OCR.

OCR means optical character recognition: converting pictures of letters into text. A vision model can also help interpret figures, but neither is enabled in the current ingestion flow.

A chart may contain meaningful trends in the drawn lines even when its caption is extractable. Reading the caption does not mean the application understood the plotted values. Likewise, flattening a financial table into text can disturb row and column alignment.

### A possible future extension

A future pipeline could detect figure regions, render relevant pages, run OCR or an appropriate vision model, create reviewed descriptions or extracted values, and keep links to the source image. A multimodal embedding model could search visual content if explicitly integrated.

Those steps need quality checks, cost controls, and provenance. We should not claim this project already handles charts simply because vectors or a language model are present.

For now, a question that depends on an image alone may lack usable evidence. Open the original report and inspect the chart manually.

## 25 Why these model choices and what they do not imply

The configured OpenAI embedding model provides compact semantic representations without installing a large embedding model on the user's laptop. The selected 1,536-dimensional output fits the small corpus and the available pgvector/NumPy path. This is a practical prototype choice, not evidence that it is the best financial embedding model in every benchmark.

The configured answer model is gpt-5-mini. It writes from retrieved passages and follows the requested source-reference format. We did not establish that it is the fastest or cheapest possible model, or that it matches a human financial analyst's accuracy.

The code calls OpenAI through HTTP requests using httpx. Embedding calls use the embeddings endpoint; generated answers use the Responses endpoint. Answer output is bounded to 2,500 output tokens in the configured adapter, and response storage is requested off through store=false.

The instruction to use only supplied sources and ignore instructions inside source text reduces some risk. It is not a formal guarantee against prompt injection or hallucination.

### Tokens are not characters

A token is a model-processing unit, often a word fragment or punctuation unit. The splitter's 1,100-character target is therefore not a 1,100-token guarantee. Input size includes instructions, the question, and selected evidence, including repeated page headers.

### Local alternatives

The code supports optional sentence-transformers/all-MiniLM-L6-v2 embeddings with 384 dimensions and Ollama generation using a separately installed model. A Cloudflare adapter also exists. These are optional code paths, not all simultaneously active services or equally validated deployment configurations.

Local models reduce reliance on paid remote inference but require downloads, storage, RAM, and processing time. Open-source tooling and a paid proprietary model can coexist in one application; they should not be described as the same licensing or cost category.

## 26 Costs memory and storage

There are several separate costs: application hosting, database hosting, API calls, local disk, local RAM, and developer effort. A free website server does not make OpenAI API calls free.

Embedding cost depends on text sent for embedding. Initial indexing sends document chunks. Later queries normally send only a question for embedding plus selected passages for answer generation. Caching document vectors reduces repeated embedding work. Answer generation has its own input and output usage.

Use current provider pricing and token counts to estimate costs. This guide does not promise a fixed number of questions for a given dollar balance. Subscription entitlements and API billing must be checked for the actual account rather than inferred from access to a chat application.

For a rough vector-memory example, 1,536 float32 numbers take 6,144 bytes. Multiplying by the recorded 2,756 vectors gives about 16.9 million raw bytes, around 16.1 MiB. That calculation excludes database overhead, JSON text, Python objects, report text, indexes, and original PDFs. SQLite JSON vectors can use substantially more storage than this raw-number estimate.

Do not confuse this example with measured database size. Actual disk and RAM usage must be measured. The current retrieval implementation can load many candidate vectors into Python, so process memory matters too.

SQLite is stored locally by default. Supabase moves database operations to an online service, but original downloaded PDFs still occupy local disk unless separately moved. Cloud storage is not a solution to every laptop memory issue, and using a cloud database does not automatically remove local model memory requirements.

## 27 Security and privacy

API keys are account credentials. The application reads them on the Python backend from a private .env file or server environment. They do not belong in HTML, browser JavaScript, screenshots, Git commits, or documentation examples.

The public repository includes a blank .env.example and ignores local environment files and data. It was created with a fresh history and a sanitized local source copy. That is a publishing precaution, not a promise that every future commit will be safe. Review each change before committing. If a real key is ever published, revoke it; merely deleting the file does not revoke access.

The local app is a single-user workspace with no user login and no public-service abuse controls. Bind it to 127.0.0.1. Do not expose that local version through a public tunnel or bind it to an internet-accessible interface as if it were a hardened multi-user product.

The Supabase schema is kept private from browser roles. Backend database credentials are still powerful and must be protected. This is not a completed tenant-isolation design for many unrelated customers. RLS enabled on tables does not by itself establish safe application authorization, especially when a privileged backend role connects.

Uploaded text is treated as untrusted data. Parameterized SQL and content-derived file paths help avoid certain injection/path problems. The prompt tells the model not to obey source-document instructions. Additional defenses would still be needed for hostile public inputs.

When remote AI is enabled, report passages and questions leave the machine for that provider. Uploading a private company document requires permission and an appropriate privacy decision, even if the original PDF remains locally saved.

## 28 The earlier hosted demo restrictions

The separately deployed version adds controls that the public local source intentionally does not include. Its configured allowances were 40 evidence-bearing research attempts per UTC day across visitors, 150 total, and 10 per browser session per UTC day. It limits concurrent research requests to two and uses an in-memory five-per-minute IP check for charged requests.

These numbers are request allowances, not a currency spending cap. A signed browser cookie separates the visible demo history. Clearing cookies can create a new browser identity; the shared daily and total database counters still apply. In-memory limits reset with the server process. The deployment was configured for one worker.

The demo blocks public document uploads, indexing, company changes, SEC company search, and AI metric extraction. It does not automatically embed missing document vectors. Its history endpoint excludes the owner's ordinary saved history.

During review, a storage-abuse gap was confirmed: no-evidence research requests can be saved without consuming those charged-request counters. Such requests do not call the AI model, but repeated requests could consume database storage. This finding was reported; it was not fixed in the version described here.

These protections reduce exposure; they do not make the service a production-grade authenticated application. The public local repository has no Render setup or demo link, so publishing that code does not automatically create a hosted instance or attach someone else's calls to the author's key.

Keeping a deployment's source repository private does not prevent people from using a publicly reachable endpoint. Access control must be implemented at the running service as well.

## 29 How to run and configure the public local version

The source is available in the public local repository. A fresh installation needs Python 3.10 or later.

```sh
git clone https://github.com/tvivekanandareddy/folio-equity-research-local.git
cd folio-equity-research-local
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

On Windows, use the Windows virtual-environment activation command and copy .env.example to .env with File Explorer or PowerShell. Open the local address only after the server starts. Leave the terminal running.

With DATABASE_URL blank, the app uses local SQLite. With AI_PROVIDER=evidence and EMBEDDING_PROVIDER=none, it returns source excerpts without calling an embedding or answer model. Upload a real report or run the download/seed steps to populate real evidence. Built-in sample excerpts are labeled illustrative.

To enable OpenAI RAG, privately set AI_PROVIDER=openai, EMBEDDING_PROVIDER=openai, your own OPENAI_API_KEY, and the chosen model names. Restart the server after environment changes. Never copy the author's account credentials into a shared guide.

To use Supabase, create your own project, privately set DATABASE_URL to your pooler URI, and run scripts/setup_database.py to apply the schema. If an explicitly configured online database fails, the app returns an error; it does not silently redirect writes to SQLite.

A clone supplies code, not the author's data or accounts. Each reader chooses and configures their own optional external services.

## 30 How the eight company library is populated

The configured company list includes Apple, Microsoft, NVIDIA, Amazon, Alphabet, Meta, Netflix, and Tesla. The scripts target a historical FY2024 corpus, not a continuously refreshed market feed.

scripts/fetch_reports.py downloads configured investor-relations documents and creates a manifest under data. PDF content is checked for expected identity/year information; Microsoft HTML is converted to TXT while the original HTML is retained locally. Download failures are recorded rather than substituted with invented reports.

scripts/seed_library.py imports company snapshots where possible and ingests downloaded manifest entries. A failed SEC snapshot can still leave verified report research usable with a warning. The script creates database records; it is not embedding the entire library by itself.

scripts/add_quarterly_reports.py adds Apple and NVIDIA Q4 documents and marks reviewed FY/Q4 coverage for relevant releases, including existing Tesla and Meta releases. Run the general download/seed steps first so required data folders and reports exist. With embeddings enabled, quarterly setup can index relevant chunks and incur provider usage.

scripts/index_library.py explicitly builds missing embeddings for saved companies. It can resume from cached completed batches.

Set SEC_USER_AGENT to an application name and your real contact email before using SEC API features. The configurable downloader catalog and the SEC company search are different mechanisms. Adding a company to the selector is not the same as obtaining and indexing every filing for it.

No background scheduler currently guarantees that the corpus is refreshed. New company/year/quarter coverage must be acquired and labeled. The “latest available Q4” means the latest present in this library, not necessarily the latest published by the company.

## 31 The source files and API routes

| File or folder | Responsibility |
|---|---|
| app/main.py | API routes, request validation, research orchestration, and source-file responses. |
| app/ingest.py | Input checks, text extraction, chunking, hashing, and document/page/chunk writes. |
| app/store.py | SQLite/PostgreSQL connections, SQL queries, source joins, text search, vectors, and history. |
| app/ai.py | Embedding providers, similarity scoring, rank fusion, answer generation, and provider errors. |
| app/research_scope.py | Quarter/year interpretation, disclosed assumptions, and missing-evidence messages. |
| app/sec.py | SEC company lookup and financial snapshot import. |
| app/static | Browser interface, styles, diagrams, and API interactions. |
| scripts | Report download, setup, seed, quarterly coverage, and embedding-index helpers. |
| supabase/schema.sql | PostgreSQL tables, pgvector extension, indexes, and browser-role restrictions. |
| tests | Isolated checks of ingestion, retrieval behavior, scope, provider adapters, and persistence. |

GET /api/health reports backend configuration and database counts without returning credentials. GET /api/companies reads company choices. GET /api/library reads report metadata. GET /api/documents returns scoped passages. GET /api/files/{id} opens a saved original. GET /api/history reads stored research.

POST /api/research processes a question. POST /api/upload ingests a report. POST /api/index computes missing embeddings. POST /api/companies imports a company. GET /api/companies/search searches SEC company identity. GET /api/metrics/extract runs AI metric extraction and writes review candidates, even though it is exposed as GET; that is an API-design limitation to improve before public multi-user use.

No autonomous agent decides which tools to execute repeatedly. This is an application-defined retrieval workflow with explicit routes and provider calls.

## 32 Troubleshooting without guessing

| Symptom | What it can mean | What to check first |
|---|---|---|
| Local page does not open | Server stopped, wrong port, or wrong machine | Confirm Uvicorn is running and use the address/port printed by that process. |
| Port 8080 is occupied | Another process is listening there | Stop the intended old process or choose another local port and use that port in the browser. |
| Database unavailable | Configured PostgreSQL cannot be reached or queried | Check database dashboard status, connection URI, network, credentials, and schema setup. Do not assume the cause. |
| Page opens but question fails | Frontend can load while backend dependencies fail | Read the visible error and check the health endpoint/configuration. |
| No quarterly answer | Requested company/quarter/year lacks usable evidence | Inspect Sources and available coverage; upload the correct release. |
| Report missing after cloning | Files and personal data are not committed | Download or upload your own documents and seed your database. |
| Scanned report rejected | There is no usable text layer | Apply an appropriate OCR process first; the current app does not do it. |
| Embeddings disabled | Default credential-free mode is active | Configure a provider only if semantic retrieval is wanted. |
| AI key rejected or quota error | Provider permissions, account balance, model access, or rate limit | Check the exact provider error and its account settings; do not expose the key. |
| Wrong-looking financial number | Bad extraction, wrong column/period, or model error | Open the original table and verify period, unit, metric definition, and sign. |

An unavailable database does not automatically mean a leaked credential. A private repository is not automatically the cause of a broken deployed app. The browser interface, server process, database, files, embedding service, and answer service are separate dependencies.

## 33 What has been tested and what has not

The public local source passed 33 automated tests when prepared. The separate hosted variant had 38 tests including five demo-control tests. Test counts describe those revisions; they should be rerun after code changes.

Tests use isolated temporary SQLite databases and mocked provider responses. They check persistence, duplicate ingestion, company and period separation, validation errors, missing files, embedding caching, provider response handling, citation fallback, quarterly interpretation, and metric-candidate quote checks.

A prior live test of the hosted configuration returned Apple's FY2024 Q4 GAAP net income with source references and verified source-file redirection. That was a useful smoke test, not a statistically representative accuracy evaluation or a promise of present availability.

The project does not currently provide a measured financial question-answer accuracy score, retrieval recall benchmark, latency service-level agreement, load-test result, comprehensive penetration test, or demonstrated million-document scale.

### A stronger future evaluation

Create a reviewed question set containing financial lookups, narrative risks, comparisons, and intentionally unanswerable questions. Record expected documents/pages, periods, units, and accepted values. Then measure whether relevant evidence appears in the top five, whether answers are supported, whether arithmetic is correct, and whether missing evidence is acknowledged.

Compare different chunk sizes, k values, embedding models, and ranking strategies against that same set. Report failures and coverage as well as successes. Automated unit tests are necessary engineering checks, but they do not replace this domain evaluation.

## 34 What we would improve next

The next work should follow demonstrated problems rather than add tools only because they are popular.

For financial reliability, improve table-aware extraction, source-column alignment, unit normalization, and reviewed factual records. Add explicit claim verification and arithmetic checks where practical.

For retrieval, evaluate chunking and k, reduce overlapping duplicate sources, and add a reranker only if it improves a measured test set. For a much larger corpus, avoid loading all candidate vectors into Python and evaluate an appropriate PostgreSQL approximate index or a specialized vector service.

For operations, introduce background ingestion/indexing jobs, document/indexing status, migrations, backups, connection pooling, and observability. Current synchronous work can take time and should not be mistaken for a production job queue.

For a public service, add authentication, per-user authorization, document ownership, complete request/body/storage limits, and provider spending controls. Fix the reported no-evidence storage-abuse gap. Protect both the application endpoints and the database; do not rely on repository privacy.

For visual evidence, add OCR or chart processing only with an explicit, tested pipeline and source-image provenance.

These are proposed improvements. They are not already delivered features, and they should not be claimed as completed work in an interview.

## 35 Common questions with direct answers

**Is PostgreSQL the vector database here?** In the online configuration, PostgreSQL stores ordinary records and pgvector embeddings together. We are not running a separate dedicated vector database.

**Are SQLite and Supabase both active for the same writes?** No. The backend selects PostgreSQL when DATABASE_URL is configured; otherwise it uses SQLite. This is not automatic database replication or failover.

**Why not store only vectors?** We need readable text, source identity, page numbers, filters, and saved work. Vectors alone are insufficient for the implemented answer-and-citation workflow. A specialized store could keep text and metadata too, but our SQL design already handles those relationships.

**Can SQL store long narrative risk text?** Yes. It is kept in TEXT columns and searched alongside metadata. We do not need to extract every paragraph into numeric facts first.

**Can NoSQL do this?** Yes. Choosing SQL was a fit and simplicity decision, not proof that NoSQL cannot support the use case.

**Does pgvector create embeddings?** No. The configured embedding provider creates them. pgvector stores vectors and offers comparison/search operations.

**Does the answer model search the database directly?** No. Python retrieves passages first, then supplies selected text to the model.

**Is the vector the financial value?** No. An embedding coordinate is a learned representation value, not Apple's revenue or a labeled financial column.

**Are all 1536 numbers meaningful to us individually?** Not as simple named financial features. Their joint representation is useful for similarity.

**Can we recover the full report from the vector?** This app does not do that. It retrieves original stored text by chunk ID. Embeddings should also not be treated as encryption.

**Does a simple Q1 question require only a simple database?** A short question can still require correct fiscal periods, evidence coverage, units, and table columns. The operational needs and data relationships still matter.

**Does one question re-embed all reports?** Normally no. Existing chunk/model embeddings are cached. A new question gets its own embedding, and missing report vectors may be indexed in local owner mode.

**Can I switch embedding models?** Yes, but the documents must be indexed in the new model's coordinate space. The current table stores one row per chunk, so the new model can replace the old row.

**Is k the number of model tokens?** No. Here k = 5 is the maximum selected passage count. Token limits and document counts are different settings.

**Why five passages rather than twenty?** It is the implemented starting setting, balancing context size and focus. It has not been proven optimal by a benchmark.

**Does an HNSW index exist?** No. The current vector search is exact; HNSW/IVFFlat are possible future changes.

**Are citations checked?** Numeric references are checked for presence and valid range. Their actual support for each generated claim is not fully verified automatically.

**Can it understand charts?** Not through the current ingestion pipeline. Extractable captions may be searchable; visual chart interpretation and OCR are not enabled.

**Can it answer about a quarter we never loaded?** It should report missing coverage rather than substitute an annual total. It does not automatically fetch every new report at query time.

**Is the assistant using live prices?** No. Its report corpus and SEC snapshots are not a live trading data feed.

**Is it a chatbot with conversation memory?** It stores research history, but does not automatically add earlier turns to each new model prompt.

**Is the entire system free?** Basic local evidence search can run without a paid API. Remote model calls, hosted infrastructure beyond allowances, and local model resource usage are separate considerations.

**Can someone copying the public code use the author's key?** The repository does not supply that key or account access. They must supply their own credentials for optional remote services. A separate public running endpoint can still consume its owner's credit if it permits requests.

**Does the public repo have a deployed website?** It contains local source and instructions. The previously hosted demo is a separate deployment from a private repository.

**Why is the project useful for an interview?** It shows end-to-end ingestion, persistence, semantic and keyword retrieval, source traceability, API integration, a usable interface, and awareness of real limitations. It is stronger to explain these accurately than to claim unsupported production scale or perfect answers.

## 36 Explaining the project in an interview

### A short explanation

I built a financial document research assistant with a Python FastAPI backend and a browser interface. It ingests company reports, extracts page text, splits it into overlapping chunks, and preserves source metadata. With OpenAI enabled, it uses text-embedding-3-small for semantic retrieval and gpt-5-mini for answers grounded in the top five retrieved passages. PostgreSQL with pgvector is the configured online store, while the public local version defaults to SQLite and evidence-only search.

### Explaining the database decision

I needed report text and embeddings together with company, period, page, and history relationships. PostgreSQL with pgvector let me combine relational records, SQL filtering, full-text search, and vector search in one database. NoSQL or a dedicated vector store could also work. I chose this design to reduce coordination between separate stores for a small project. SQLite provides a simpler local setup, with vectors stored as JSON and similarity calculated in Python.

### Explaining an engineering challenge

Short financial questions were not just ordinary word search. A question such as q4 income needed the correct available fiscal quarter, an explicit interpretation of income, and the quarterly table column rather than the annual total. I added scope resolution and reviewed period coverage, preserved page headers with quarterly excerpts, and made missing evidence visible. The pipeline still needs better table extraction and claim-level verification.

### Explaining limitations honestly

The system has source-reference checks and tests, but it does not guarantee that every generated number is correct. It does not interpret charts, automatically refresh every filing, or provide benchmarked production-scale retrieval. The public repository is intended for local execution, and a multi-user public service would require stronger authentication, authorization, and abuse controls.

These explanations describe the implemented project. They should be adjusted if the architecture or provider configuration changes later.

## 37 Glossary for quick reference

| Term | Plain meaning |
|---|---|
| Annual report or 10-K | A company's yearly financial and business report; a 10-K is a US SEC annual filing. |
| Ticker | A short market identifier such as AAPL. |
| Fiscal year | The company's chosen accounting/reporting year. |
| Q1 through Q4 | The four quarters within that fiscal reporting year. |
| Revenue or net sales | Sales-related income before the relevant costs and expenses. |
| Net income | Profit after the relevant expenses and taxes. |
| GAAP | Generally accepted accounting principles in the reporting context. |
| Metadata | Information describing a document or passage, such as title and year. |
| Provenance | Where information came from and how to trace it back. |
| Ingestion | Bringing a document into the application and preparing its records. |
| Chunk | A smaller searchable passage taken from a document. |
| Embedding | A numerical representation produced by a model. |
| Vector | An ordered list of numbers; an embedding is a vector used for representation. |
| Dimension | One coordinate in a vector. |
| Semantic search | Finding text by learned similarity of meaning. |
| Keyword search | Finding text using words or terms in the content. |
| Hybrid retrieval | Combining different retrieval rankings. |
| Cosine similarity | A numerical comparison of vector direction. |
| RRF | Reciprocal rank fusion; combining rankings through rank-based contributions. |
| Retrieval k | The maximum number of selected results in a retrieval stage. |
| Index | A data structure that helps a system find records; different indexes serve different searches. |
| HNSW | An approximate nearest-neighbor vector index; not enabled in this project. |
| LLM | Large language model; a model that processes and generates language. |
| Prompt | Instructions and input supplied to a model for a request. |
| Context | The information the model can use in that request, including retrieved passages. |
| Hallucination | Unsupported or incorrect generated content. |
| RAG | Retrieval-augmented generation; find evidence and supply it to a generator. |
| OCR | Extracting text from images of text. |
| SQL | A language for working with relational database records. |
| pgvector | A PostgreSQL extension for vector storage and similarity search. |
| Supabase | The managed PostgreSQL service used for the optional online database. |
| Transaction | A group of database operations committed or rolled back together. |
| Hash | A content fingerprint used here for identity and duplicate detection. |
| API key | A private credential authorizing access to a provider account. |
| Environment variable | A process setting used to supply configuration privately. |
| Localhost | The current computer, commonly reached using 127.0.0.1. |

## 38 Sources and implementation references

The implementation facts in this guide come from app/main.py, app/ingest.py, app/store.py, app/ai.py, app/research_scope.py, app/sec.py, the report/setup scripts, schema files, tests, and the separately prepared public local source. The public local version removes the hosted-demo middleware and usage table. Public source: https://github.com/tvivekanandareddy/folio-equity-research-local.

The following primary sources support external tool concepts and the worked financial values. They are references for learning, not claims that every capability in those products is enabled in Folio.

- [S1] OpenAI vector embeddings guide. Default embedding dimensions and embedding concepts. https://developers.openai.com/api/docs/guides/embeddings
- [S2] pgvector official project documentation. PostgreSQL vector storage, cosine operators, exact search, and optional approximate indexes. https://github.com/pgvector/pgvector
- [S3] SQLite serverless architecture documentation. Embedded database operation without a separate database server. https://www.sqlite.org/serverless.html
- [S4] Apple Q4 and FY2024 consolidated financial statements, physical PDF page 1. Annual net sales, quarterly and annual period columns, and GAAP net income used in the worked examples. https://www.apple.com/newsroom/pdfs/fy2024-q4/FY24_Q4_Consolidated_Financial_Statements.pdf
- [S5] Chroma official introduction. Document, metadata, and retrieval capabilities. https://docs.trychroma.com/docs/overview/introduction
- [S6] Qdrant official overview. Vector retrieval and related filtering/hybrid-query documentation. https://qdrant.tech/documentation/overview/
- [S7] FAISS official documentation. Vector similarity search library. https://faiss.ai/
- [S8] PostgreSQL JSON type documentation. PostgreSQL can store JSON and ordinary text; Folio's current payload columns use TEXT. https://www.postgresql.org/docs/current/datatype-json.html

