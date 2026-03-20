# PR Assistant

## Project Overview
PR Assistant is an AI-first pull request review system delivered as a GitHub App. It receives `pull_request` webhooks, collects PR metadata and diffs from GitHub, derives structured signals with deterministic logic, and requires AI to generate the final review outputs. The product is designed for high-signal, explainable review guidance rather than generic automation or noisy inline comments.

## Product Goal
Help engineers understand pull request risk and review focus quickly by combining deterministic repository analysis with AI-generated summaries, findings, and test guidance. The system must produce concise, reliable outputs that are explainable from the underlying diff and signals.

## MVP Scope
- GitHub App integration for pull request webhook intake
- FastAPI service as the only application runtime
- Pull request metadata, changed files, and unified diff retrieval from GitHub
- Rails-first file classification only
- Deterministic signal generation from file paths and diff metadata
- Numeric risk score plus `LOW` / `MEDIUM` / `HIGH` label
- Mandatory AI generation of:
  - PR summary
  - Risk explanation
  - Key findings
  - Test gap suggestions
- Posting one concise review summary comment back to GitHub
- Support for free or local AI providers in v1, including Ollama

## Core Architecture
1. GitHub sends a `pull_request` webhook to the FastAPI endpoint.
2. The webhook layer validates the request and extracts repository, PR number, and event metadata.
3. The GitHub client fetches PR metadata, changed files, and diffs.
4. The classifier assigns Rails-first file categories from file paths.
5. The signal layer computes structured indicators from file metadata and diff characteristics.
6. The risk scorer calculates a numeric score and maps it to `LOW`, `MEDIUM`, or `HIGH`.
7. The AI input builder packages PR context, classified files, signals, risk indicators, and diff excerpts into a structured prompt payload.
8. The AI layer generates the final summary, risk explanation, findings, and test suggestions.
9. The formatter constrains output to a concise review shape.
10. The GitHub client posts a single review summary comment to the pull request.

## Main Domain Models
- `PullRequest`: repository, PR number, title, body, author, base branch, head branch, changed file count, additions, deletions
- `ChangedFile`: path, status, additions, deletions, patch availability, classified category
- `DiffChunk`: file path, hunk headers, patch text, line counts, change density
- `FileClassification`: category, confidence, rationale
- `Signal`: name, value, severity, evidence
- `RiskAssessment`: numeric score, label, contributing signals
- `AIReviewInput`: structured PR context, signals, risk assessment, selected diff content
- `AIReviewOutput`: summary, risk explanation, findings, test gaps, confidence notes
- `GitHubReviewComment`: final rendered markdown comment

## Rails-First File Classification Categories
Only Rails-oriented categories are supported in v1. Do not introduce framework-agnostic abstraction.

- Models: `app/models/**`
- Controllers: `app/controllers/**`
- Views: `app/views/**`
- Helpers: `app/helpers/**`
- Services: `app/services/**`
- Jobs: `app/jobs/**`
- Mailers: `app/mailers/**`
- Policies / Authorization: `app/policies/**`
- Serializers / Presenters: `app/serializers/**`, `app/presenters/**`
- Components: `app/components/**`
- JavaScript / Frontend assets in Rails app: `app/javascript/**`, `app/assets/**`
- Config: `config/**`
- Routes: `config/routes.rb`
- Database schema: `db/schema.rb`
- Migrations: `db/migrate/**`
- Specs / Tests: `spec/**`, `test/**`
- Initializers: `config/initializers/**`
- Gem dependencies: `Gemfile`, `Gemfile.lock`
- CI / automation: `.github/workflows/**`
- Documentation: `README*`, `docs/**`
- Other Rails-adjacent files: any remaining repository files, classified conservatively

## Initial Signals
Signals should be explicit, small, and explainable. Initial v1 signals include:

- `files_changed_count`
- `additions_count`
- `deletions_count`
- `large_diff`
- `high_churn_file`
- `migration_present`
- `schema_changed`
- `routes_changed`
- `initializer_changed`
- `gemfile_changed`
- `model_changed`
- `controller_changed`
- `service_changed`
- `policy_changed`
- `test_files_changed`
- `no_tests_changed`
- `ci_config_changed`
- `sensitive_config_changed`
- `multiple_core_layers_touched`
- `docs_only_change`

## Rule Engine Role
The rule engine exists to generate structured signals and risk indicators, not to make the final review judgment on its own. It should:

- Normalize raw GitHub and diff data into stable, testable signals
- Detect notable change patterns from Rails file categories and diff metadata
- Produce evidence that can be passed directly to AI
- Support explainable scoring inputs

It must not replace AI-generated review output or attempt to emit full human-facing findings as the final product.

## Risk Scoring Approach
Risk scoring is deterministic and transparent.

- Compute a numeric score from weighted signals
- Use clear thresholds to map score to `LOW`, `MEDIUM`, or `HIGH`
- Increase weight for signals such as migrations, routes changes, initializer changes, dependency changes, broad multi-layer edits, and large diffs
- Reduce score for narrow, docs-only, or test-only changes where appropriate
- Store the top contributing signals for downstream explanation

The score is an input to AI interpretation, not a replacement for AI-written reasoning.

## Review Output Expectations
The final GitHub comment should be concise, high-signal, and easy to scan.

- One short PR summary
- One risk explanation tied to actual signals
- Up to 3 to 5 findings only
- Targeted test gap suggestions
- No low-confidence filler
- No excessive inline review behavior in MVP

Every output should be traceable to the diff, metadata, or structured signals.

## Engineering Rules
- Keep v1 Rails-first only
- Do not build multi-framework abstraction in v1
- Do not add background jobs in v1
- Do not depend on paid AI APIs in v1
- AI is mandatory for final output generation
- Deterministic logic must support AI, not replace it
- Prefer simple, testable modules over speculative architecture
- Optimize for signal quality, not feature count
- Minimize moving parts in the webhook-to-comment path
- Keep prompts structured and versioned
- Keep risk scoring rules explicit and unit-testable
- Fail safely when AI output is missing or malformed

## AI-First Design
AI is mandatory in this system. PR Assistant is not a generic LLM wrapper and not a rules-only analyzer with optional AI polish.

### AI Is Responsible For
- Summarizing PR changes
- Interpreting structured signals
- Generating human-readable findings
- Suggesting test cases
- Prioritizing issues

### Deterministic Components Are Responsible For
- File classification
- Signal generation
- Risk indicators
- Providing structured context to AI

### AI Must
- Use structured inputs composed of signals and diff/context
- Generate concise, high-signal output
- Limit findings to a maximum of 3 to 5
- Avoid generic or low-confidence suggestions

### AI Must Not
- Hallucinate facts not present in the diff or structured context
- Generate excessive comments
- Replace deterministic scoring logic

## Testing Expectations
- Unit tests for file classification rules
- Unit tests for signal generation
- Unit tests for risk scoring thresholds and weights
- Contract tests for GitHub webhook parsing
- Integration tests for webhook-to-comment flow with mocked GitHub and AI providers
- Prompt-shape tests to ensure AI input contains required structured context
- Output validation tests for concise review formatting and finding count limits

## Non-Goals
- No end-user frontend in MVP
- No inline per-file or per-line review comments in MVP
- No autonomous code modification
- No support for non-Rails repositories in v1
- No generalized plugin system
- No background processing architecture before it is needed
- No paid-model dependency as a requirement

## Future Extension Path
- Additional Rails-specific signals and heuristics
- Better diff selection and chunk prioritization for AI context
- Stronger review explanation with signal-to-output traceability
- Optional support for queued processing if runtime pressure demands it
- Provider abstraction for multiple free or local AI backends
- Carefully scoped expansion beyond Rails after v1 proves signal quality

## Definition Of Success For MVP
- Webhook ingestion to GitHub comment works reliably
- Rails file classification is deterministic and correct for common project layouts
- Risk score and label are explainable from explicit signals
- AI output is required, concise, and useful
- Review comments surface meaningful summary, risk, findings, and test gaps
- Output stays high-signal with minimal noise
- The system remains simple enough to maintain and iterate quickly

## Agent Instructions
- Preserve the AI-first architecture in all design and implementation decisions
- Keep deterministic analysis focused on structured context generation
- Do not introduce features that turn the product into a generic LLM wrapper
- Keep v1 scoped to Rails-first repository analysis only
- Prefer a single synchronous request path in MVP
- Avoid over-engineering abstractions, orchestration, or framework support
- Ensure every human-facing review output is AI-generated from structured inputs
- Keep GitHub as the primary interaction surface
- Optimize for one strong review summary rather than many weak comments
- When extending rules or signals, make them explicit, testable, and explainable
