# PR Assistant Phases

## Phase 1: Project Skeleton
### Covers
- FastAPI app setup
- Basic project structure
- Configuration loading
- Health check endpoint
- Local development setup

### Exit Criteria
- Service starts locally
- Environment configuration is validated at startup
- Health endpoint responds successfully

### Test After Flow
- App boots without runtime errors
- Required environment variables are handled correctly
- Health endpoint returns expected status and payload

## Phase 2: GitHub App Webhook Intake
### Covers
- `pull_request` webhook endpoint
- GitHub signature validation
- Parsing core webhook payload fields
- Event filtering for supported PR actions only

### Exit Criteria
- Valid GitHub webhook requests are accepted
- Invalid signatures are rejected
- Unsupported events are ignored safely

### Test After Flow
- Valid signed webhook reaches handler successfully
- Invalid signature returns rejection response
- Unsupported action does not trigger review flow
- Minimal and full webhook payloads parse correctly

## Phase 3: GitHub PR Data Fetching
### Covers
- GitHub API client
- Fetching PR metadata
- Fetching changed files
- Fetching unified diffs or patch data
- Basic API error handling

### Exit Criteria
- Service can retrieve all required PR context from GitHub
- Failure paths are explicit and safe

### Test After Flow
- PR title, body, branches, author, and counts are fetched correctly
- Changed file list includes status and churn metadata
- Diff or patch content is available for supported files
- GitHub API errors are surfaced cleanly

## Phase 4: Rails-First File Classification
### Covers
- Path-based file classification for Rails repositories
- Classification categories for models, controllers, services, views, routes, migrations, tests, config, dependencies, and CI
- Conservative fallback category for uncategorized files

### Exit Criteria
- Common Rails paths classify deterministically
- Classification output is stable and explainable

### Test After Flow
- Representative Rails paths map to expected categories
- Edge-case files are handled predictably
- Mixed PRs produce correct per-file categories

## Phase 5: Signal Generation
### Covers
- Structured signal extraction from file paths and diff metadata
- Initial v1 signals such as migrations, routes changes, initializer changes, large diffs, test presence, and multi-layer edits
- Signal evidence capture for explainability

### Exit Criteria
- Signals are deterministic
- Signals are tied to explicit evidence from the PR data

### Test After Flow
- Each signal triggers only under expected conditions
- Signal evidence references the correct files or metadata
- Docs-only and test-only changes are recognized correctly

## Phase 6: Risk Scoring
### Covers
- Weighted scoring model
- Mapping numeric score to `LOW`, `MEDIUM`, or `HIGH`
- Tracking top contributing signals

### Exit Criteria
- Risk score is deterministic and explainable
- Threshold behavior is stable

### Test After Flow
- Known PR shapes produce expected score ranges
- High-risk changes score higher than narrow low-risk changes
- Threshold boundaries map to the correct label
- Contributing signals are preserved for explanation

## Phase 7: AI Provider Setup
### Covers
- Groq provider configuration for development and production
- Default model selection for Groq review generation
- Groq request shape preparation for review generation
- Validation of required Groq credentials and base URL

### Exit Criteria
- Service can resolve a valid AI provider configuration at startup
- Provider-specific request construction is deterministic and testable

### Test After Flow
- Groq configuration requires an API key
- Provider factory returns the expected request shape
- Default model selection is stable

## Phase 8: AI Review Input Builder
### Covers
- Structured prompt payload assembly
- Inclusion of PR metadata, classified files, signals, risk indicators, and selected diff content
- Prompt templates for summary, findings, and test gap generation

### Exit Criteria
- AI input is structured, concise, and complete
- Prompt shape is stable and versioned

### Test After Flow
- Prompt includes required metadata and signals
- Prompt excludes unnecessary noise
- Large PRs are truncated or summarized predictably
- Prompt payload format remains consistent across runs

## Phase 9: AI Review Generation
### Covers
- AI provider interface for free or local models such as Ollama
- Mandatory AI generation of:
  - PR summary
  - Risk explanation
  - Key findings
  - Test gap suggestions
- Output validation and fallback handling

### Exit Criteria
- AI output is required for final review generation
- Output format is parseable and concise

### Test After Flow
- AI returns all required review sections
- Findings remain limited to 3 to 5 items
- Generic or unsupported claims are filtered or rejected
- Missing or malformed AI output fails safely

## Phase 10: Review Formatting And GitHub Comment Posting
### Covers
- Final markdown review formatter
- Single concise summary comment for GitHub
- GitHub comment posting client
- Idempotency or duplicate-post protection if needed

### Exit Criteria
- A clean review summary comment is posted to the PR
- Output is readable and high-signal

### Test After Flow
- Comment renders correctly in GitHub markdown
- Risk label, summary, findings, and test gaps appear in expected order
- Duplicate webhook delivery does not create noisy repeated comments
- GitHub posting errors are handled safely

## Phase 11: End-to-End MVP Validation
### Covers
- Full webhook-to-comment flow
- Integration of deterministic analysis with mandatory AI output
- Operational readiness for MVP usage

### Exit Criteria
- Pull request webhook can produce a final GitHub comment end to end
- Output quality is concise, explainable, and useful

### Test After Flow
- Run a full PR scenario from webhook receipt to posted comment
- Validate traceability between diff, signals, score, and AI output
- Validate low-risk, medium-risk, and high-risk example PRs
- Confirm docs-only and test-only PRs remain low-noise
- Confirm migration or routes-heavy PRs surface higher risk and stronger findings

## Recommended Delivery Order
1. Phase 1: Project Skeleton
2. Phase 2: GitHub App Webhook Intake
3. Phase 3: GitHub PR Data Fetching
4. Phase 4: Rails-First File Classification
5. Phase 5: Signal Generation
6. Phase 6: Risk Scoring
7. Phase 7: AI Provider Setup
8. Phase 8: AI Review Input Builder
9. Phase 9: AI Review Generation
10. Phase 10: Review Formatting And GitHub Comment Posting
11. Phase 11: End-to-End MVP Validation

## MVP Testing Summary
- Unit tests for classification, signals, and scoring
- Contract tests for webhook parsing and GitHub client behavior
- Integration tests for webhook-to-comment flow with mocked GitHub and AI
- Output validation tests to enforce concise, high-signal review structure
- Regression fixtures for representative Rails PR examples
