# RAG Planning Skill

## Goal

Decide when a task plan should include a `rag_search` step.

## Use rag_search when

- The user asks to answer based on the local knowledge base.
- The user mentions saved materials, indexed URLs, documents, notes, articles, or reference material.
- The task asks to explain, summarize, compare, or answer something that may exist in the knowledge base.
- The task requires factual context that is not provided in the current conversation.
- The user asks about previously ingested content.

## Do not use rag_search when

- The user provides all necessary content directly in the message.
- The task is simple translation, rewriting, formatting, calculation, or brainstorming.
- The task is general coding or architecture advice that does not require stored knowledge.
- The user explicitly says not to search the knowledge base.

## Use add_urls when

- The user explicitly asks to add URLs to the knowledge base.
- The user explicitly asks to save, ingest, index, or persist URLs.

## Do not use add_urls when

- A URL merely appears in the task.
- The user only asks to summarize a URL once.
- The user did not ask to save the URL for future retrieval.

## Planner output rule

When using `rag_search`, every step must include a clear `reason`.

## rag_search query rule

- Build the search query from the language and wording most likely to appear in the knowledge base.
- Preserve exact product names, document titles, URLs, filenames, identifiers, ASINs, issue names, and quoted phrases from the user message.
- If the user asks in Chinese but includes English entities or the knowledge base is likely English, keep the English entities and add English keywords.
- Do not over-compress the query into generic words like "reason", "summary", or "information" when the user provided specific terms.
- For product reviews, include the product title, rating, ASIN if available, and concrete review phrases such as "leaked", "smell", "not durable", or other distinctive words.
