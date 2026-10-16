# Architecture

```text
Resident request
   -> Streamlit interface
   -> CivicRequestHarness
       -> loads civic-request-intake/SKILL.md
       -> OllamaModelAdapter (configurable local open-weight model)
       -> Pydantic schema validation
   -> Resident reviews structured draft
   -> Minimal audit event (no raw request content)

Sample report set -> simple lexical duplicate hints -> human review only
```

This is a local prototype and does not connect to official municipal APIs. The duplicate-matching function is a lexical baseline, not semantic AI. It must be evaluated and could be replaced by embedding-based similarity in a later iteration.
