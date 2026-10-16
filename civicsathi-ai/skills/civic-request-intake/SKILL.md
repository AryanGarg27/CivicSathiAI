---
name: civic-request-intake
description: Helps understand civic-service requests, classify public grievances, extract relevant details, identify missing information, and suggest a next service workflow. Use when a resident asks about a civic issue or municipal service.
license: Apache-2.0
metadata:
  project: civicsathi-ai
  version: "0.1.0"
---

# Civic Request Intake

## Purpose
Help residents describe their civic-service request clearly and consistently.

## Workflow
1. Understand the request and preferred language.
2. Identify the likely request type using the provided service catalogue.
3. Extract relevant information, including issue summary and any location explicitly provided by the resident.
4. List missing information without inventing values.
5. Return a structured draft for resident review.
6. Suggest possibly related reports for human review when available.
7. Explain uncertainty and use a safe fallback when classification is unclear.

## Constraints
- Never invent a complaint ID, official response, or case status.
- Never claim a complaint was submitted unless an authorized submission tool confirms it.
- Do not automatically reject reports based on similarity.
- Do not approve applications, enforce regulations, or close cases.
- Minimize personal information and keep raw request text out of audit logs.
- Require resident confirmation before consequential actions.

## Expected output
Return a validated object containing `request_type`, `category`, `summary`, `location`, `missing_information`, `suggested_service`, `confidence`, and `needs_human_review`.
