# Evaluation Pipeline

How unevaluated job postings get scored and matched against a profile's resume.
Implemented in `app/evaluator.py`.

## Flow Chart

```mermaid
flowchart TD
    A["POST /api/profiles/{id}/evaluate"] --> B["Load Profile"]
    B --> C["Load resume_text\nfrom profile"]

    C --> D["Query job_postings\nWHERE profile_id = id\nAND status = 'new'"]

    D --> E["For each job"]

    E --> F{"Profile has custom\nevaluator_prompt?"}

    F -->|Yes| G["Use custom prompt\nas system message"]
    F -->|No| H["Build default prompt:\n• Persona: Senior hiring evaluator\n• Scoring rubric\n• Cover letter instructions"]

    G --> I["Build ChatPromptTemplate\nSystem: evaluator prompt\nHuman: resume + job description"]
    H --> I

    I --> J["ChatAnthropic\nClaude Sonnet 4\n.with_structured_output\nJobEvaluation"]

    J --> K["Receive structured output:\n• match_score (1-100)\n• match_reasoning\n• cover_letter"]

    K --> L["UPDATE job_postings\nSET score, reasoning,\ncover_letter,\nstatus = 'evaluated',\ndate_evaluated = now()"]

    L --> M["Rate limit delay"]
    M --> E

    E -->|All jobs done| N["Return summary:\n• jobs evaluated\n• avg score\n• top matches"]
```

## LangChain Components

| Component | Usage |
|-----------|-------|
| `ChatAnthropic` | LLM wrapper for Claude Sonnet 4 |
| `ChatPromptTemplate` | System + human message construction |
| `.with_structured_output()` | Enforces `JobEvaluation` Pydantic schema |
| Chain (`prompt \| model`) | Composes the pipeline |
