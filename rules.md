# Engineering Rules & Development Standards
## Project: KidSync AI
### Document Version: 1.0.0 | Status: Active Engineering Protocol

---

## 1. Core Engineering Principles

Every engineer, AI agent, and automated contributor working on the **KidSync AI** codebase must adhere to the following core tenets:

1. **Child Privacy & Safety Over Features:** Never sacrifice data privacy, confidentiality, or security for speed or convenience. A child's sensitive medical, location, or behavioral data must never be exposed or improperly stored.
2. **Deterministic Boundaries for AI:** Artificial intelligence is a co-pilot, mediator, and summarizer—never an autonomous arbiter of custody or emergency medical truth. All AI outputs must be bounded by strict validation schemas and fail-safe fallbacks.
3. **Court-Ready Immutability:** Financial ledgers, communications, and custody agreements carry legal weight. Under no circumstances may code allow silent physical deletion or un-audited modification of records designated as legal evidence.
4. **Offline-First by Design:** Assume the user has spotty cellular coverage in doctor's offices, school basements, or rural drop-off zones. The mobile client must be 100% operational offline for viewing and logging.
5. **Calm, High-Empathy UX:** Code and design must avoid sensationalist notifications, aggressive red alerts, or guilt-inducing copy. De-escalation starts with our software.

---

## 2. Codebase Conventions & Language Standards

### 2.1 TypeScript Strictness & Typing Protocols
- **Strict Mode Mandatory:** All `tsconfig.json` configurations must enforce:
  ```json
  {
    "compilerOptions": {
      "strict": true,
      "noImplicitAny": true,
      "strictNullChecks": true,
      "strictFunctionTypes": true,
      "noImplicitThis": true,
      "noUnusedLocals": true,
      "noUnusedParameters": true,
      "exactOptionalPropertyTypes": true,
      "noFallthroughCasesInSwitch": true
    }
  }
  ```
- **Ban on `any`:** The use of `any` is strictly prohibited. Use `unknown` with runtime type narrowing or generic constraints. Any PR containing `any` without an explicit, approved comment exception will fail CI.
- **Runtime Validation with Zod:** All external inputs—including HTTP request bodies, query params, WebSocket messages, environment variables, and LLM responses—**must** be validated through Zod schemas before being processed by application logic.
- **No Floating Promises:** All asynchronous calls must be explicitly `await`ed or handled with `.catch()`. The `@typescript-eslint/no-floating-promises` rule is set to `error`.

### 2.2 Monorepo Structure & Module Boundaries
The repository follows a clean Turborepo monorepo architecture:

```
kidsync-ai/
├── apps/
│   ├── mobile/             # React Native / Expo application (iOS & Android)
│   ├── web/                # Next.js 14 App Router web portal
│   └── docs/               # Technical & API documentation
├── packages/
│   ├── api-client/         # Shared typed SDK for REST & WebSocket APIs
│   ├── database/           # Prisma / Kysely schemas, migrations, seeders
│   ├── ai-engine/          # Gemini API orchestration, prompt templates, evaluators
│   ├── shared-types/       # Canonical TypeScript models, enums & DTOs
│   ├── validation/         # Zod schemas for forms, APIs, and AI outputs
│   ├── ui-kit/             # Cross-platform design tokens & React components
│   └── crypto-audit/       # Merkle-chain, hashing, and court export utilities
├── tools/                  # Build scripts, CI tools, lint configs
├── prd.md                  # Product Requirements Document
├── architecture.md         # System Architecture & Technical Specs
├── rules.md                # Development Rules & Engineering Standards (This file)
├── phase.md                # Implementation Roadmap & Milestone Tracker
└── design.md               # UI/UX Design System Specifications
```

- **Dependency Inversion:** Applications (`apps/*`) depend on packages (`packages/*`). Packages **must never** depend on applications or have circular references.
- **Shared Code First:** If a data model, validation rule, or utility is utilized in both mobile and web, it must reside in `@kidsync/shared-types` or `@kidsync/validation`.

### 2.3 React & React Native Coding Standards
- **Functional Components & Hooks Only:** Class components are forbidden.
- **Deterministic Component Props:** Use explicitly defined TypeScript interfaces for all component props. Default export is forbidden for components; use named exports:
  ```typescript
  // GOOD:
  export interface HandoffCardProps {
    readonly childId: string;
    readonly digest: HandoffDigest;
    readonly onAcknowledge: (digestId: string) => Promise<void>;
  }

  export const HandoffCard: React.FC<HandoffCardProps> = ({ childId, digest, onAcknowledge }) => { ... };

  // BAD:
  export default function HandoffCard(props: any) { ... }
  ```
- **Immutable State Updates:** Never mutate state directly. Always use functional updates or immer for nested state manipulations.
- **Memoization Rules:** Do not prematurely optimize with `useMemo` or `useCallback` unless handling heavy calculations, list renderers (`FlatList`), or dependencies in custom hooks.

---

## 3. AI & LLM Engineering Protocols

### 3.1 Prompt Management & Sandboxing
- **Location of Prompts:** All prompts must be stored in `@kidsync/ai-engine/prompts/` as parameterized template functions. Never hardcode prompt strings inside React components or API route handlers.
- **System Prompt Isolation:** System instructions must explicitly instruct the model on its boundary conditions:
  > *"You are the KidSync AI Peacekeeper Engine. Your role is strictly to analyze tone, detect hostility, and propose neutral, child-centric rewrites adhering to Non-Violent Communication (NVC). You do not offer legal advice, medical prescriptions, or subjective personal commentary."*
- **Parameter Pinning:**
  - Tone Moderation: `temperature: 0.1`, `topP: 0.8` (ensures consistent, deterministic classification).
  - Multimodal OCR & Receipt Parsing: `temperature: 0.0` (zero creative variance).
  - Handoff Digest Generation: `temperature: 0.2` (concise, factual summarization).

### 3.2 Structured Output Enforcement
Every LLM call must be constrained to return JSON conforming to a specific Zod schema:

```typescript
// Example: Peacekeeper Tone Schema
export const ToneAnalysisResultSchema = z.object({
  sentimentScore: z.number().min(-1.0).max(1.0),
  isConflictDetected: z.boolean(),
  detectedTriggers: z.array(z.enum([
    'BLAME',
    'ACCUSATION',
    'CONTEMPT',
    'PASSIVE_AGGRESSIVE',
    'SARCASM',
    'DEMANDING'
  ])),
  confidence: z.number().min(0.0).max(1.0),
  nvcSuggestion: z.string().nullable(),
  reasoningBrief: z.string().max(120)
});

export type ToneAnalysisResult = z.infer<typeof ToneAnalysisResultSchema>;
```

- **Retry & Fallback Circuit:** If the LLM produces invalid JSON, retry once with an error-correcting prompt. If that fails, trip the circuit breaker and return a safe deterministic fallback without crashing the user flow.

### 3.3 Privacy & PII Scrubbing Rules
- **Rule:** No child full name, residential address, telephone number, social security number, or government health identifier may be included in raw LLM prompt text.
- **Implementation:** The `@kidsync/ai-engine/sanitizer` must tokenize identifiable fields (`[CHILD_1]`, `[DATE_1]`) before external dispatch, then re-hydrate the result locally on the client or backend before persisting.

---

## 4. Database, Security & Legal Evidence Rules

### 4.1 Append-Only Audit Chain Integrity
- **No Physical DELETE on Audit Tables:** Tables `chat_messages`, `expense_records`, `custody_swaps`, and `audit_log_entries` are strictly append-only.
- **Soft Deletion Protocol:** If a user requests hiding a message or expense, update `is_hidden = true`, `hidden_by = userId`, `hidden_at = timestamp`. The physical record remains preserved in the cryptographic audit chain.
- **Hash Chaining Validation:** Every audit entry must verify that `prev_entry_hash` matches the cryptographic hash of the prior record in the family's chain. Any hash mismatch raises a critical security alert (`ALERT_TAMPER_DETECTED`).

### 4.2 Row-Level Security (RLS) & RBAC Enforcement
- Every database query touching family or child data must explicitly verify the requesting user's active membership in `caregiver_roles`.
- Queries must use parameterized statements or ORM type-safe builders to prevent SQL injection.
- Role capability checks must occur before any business logic executes:
  ```typescript
  // Enforce capability before operation
  await rbacService.assertPermission(currentUserId, familyId, 'FINANCIALS_MANAGE');
  ```

---

## 5. Error Handling, Logging & Observability

### 5.1 Standardized Error Taxonomy
All application errors must inherit from `KidSyncBaseError`:

| Error Class | HTTP Status | Purpose | Retryable |
| :--- | :--- | :--- | :--- |
| `ValidationError` | 400 Bad Request | Invalid user input or schema failure | No |
| `AuthenticationError` | 401 Unauthorized | Missing or expired token | No (re-auth) |
| `AuthorizationError` | 403 Forbidden | User lacks required caregiver role | No |
| `ResourceNotFoundError` | 404 Not Found | Child, event, or expense missing | No |
| `ConflictError` | 409 Conflict | Custody date clash or vector clock divergence | Yes (re-fetch) |
| `AIServiceUnavailableError` | 503 Service Unavailable | Gemini API timeout or rate-limit | Yes (exponential backoff) |

### 5.2 Logging Guardrails
- **Zero Sensitive Data in Logs:** Never log passwords, tokens, full child names, medical diagnoses, credit cards, or raw chat messages into application logs (Console, Datadog, Sentry).
- **Log Format:** Structured JSON logs containing `timestamp`, `level`, `traceId`, `service`, `eventType`, and sanitized context.

---

## 6. Testing & Quality Assurance Gates

### 6.1 Automated Coverage Thresholds
- **Unit Tests:** $\ge 85\%$ line coverage across all packages.
- **Critical Business Paths:** $100\%$ test coverage required for:
  - Cryptographic audit hashing and Merkle verification
  - Medication administration timing and dosage validation
  - Expense split calculations and currency math
  - RBAC permission checking middleware
  - Tone analysis and NVC rewriting fallback behaviors

### 6.2 Testing Layers & Tooling
- **Unit & Integration:** Vitest / Jest with mock databases or Testcontainers PostgreSQL.
- **E2E Testing:** Playwright for Web portal; Detox / Maestro for mobile app user journeys.
- **AI Regression Benchmarks:** Maintain a suite of 250 standardized co-parenting messages with known conflict levels to verify that prompt modifications do not increase false positives or missed hostility.

---

## 7. Git Workflow, Branching & Commit Protocol

### 7.1 Conventional Commits
All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

$$\text{type}(\text{scope}):\ \text{short description}$$

- `feat(calendar)`: Add 2-2-5-5 custody template generator
- `fix(meds)`: Prevent duplicate dose submission when offline
- `perf(sync)`: Optimize WatermelonDB batch sync serialization
- `test(audit)`: Add unit tests for SHA-256 Merkle chain verification
- `docs(api)`: Update OpenAPI documentation for custody swaps

### 7.2 Pull Request (PR) Requirements
Every Pull Request must satisfy:
1. All automated CI checks green (Lint, Typecheck, Unit Tests, Security Vulnerability Scans).
2. No new TypeScript warnings or ESLint suppressions.
3. PR description includes:
   - Summary of changes
   - Associated issue / user story ID
   - Manual testing proof (screenshots or video for UI changes)
   - Privacy & COPPA impact assessment ("Does this touch child data? If so, how is it protected?")
4. Approval from at least one core engineering reviewer.
