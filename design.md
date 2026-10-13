# UI/UX Design System & Experience Specifications
## Project: KidSync AI
### Document Version: 1.0.0 | Status: Design System Baseline

---

## 1. Design Philosophy & Emotional UX

### 1.1 De-Escalating & Low-Cortisol Design
Parenting—particularly across divided households or while managing neurodivergent routines—is emotionally demanding and mentally exhausting. The interface of **KidSync AI** is intentionally crafted as a **safe, calming, low-cortisol digital sanctuary**.

- **Non-Adversarial Visual Language:** Eliminates harsh, accusatory reds, flashing alerts, and punitive visual metaphors. Warnings are rendered in soft ambers and muted slates rather than sirens.
- **Cognitive Offload & Glanceability:** Caregivers under sleep deprivation or stress must be able to understand the current state of their child within 3 seconds of opening the application.
- **Graceful Mediation:** AI intervention is presented as a supportive assistant rather than a lecturing censor. Rewrites are framed as "offers" that empower the user rather than moral rebukes.
- **Accessibility as a Right:** Total compliance with WCAG 2.1 AA (and AAA for critical medical cards), ensuring usability under direct sunlight, in dark nurseries, or with one hand while holding an infant.

---

## 2. Color Palette & Design Tokens

The color architecture is built around calming earth tones, serene blues, and soft botanical greens that physiologically promote calm and emotional stability.

### 2.1 Color Tokens & Hex Specifications

| Token Name | Light Mode Hex | Dark Mode Hex | Semantic Role & Purpose |
| :--- | :--- | :--- | :--- |
| `--color-canvas-bg` | `#F8FAFC` | `#0F172A` | Primary background canvas |
| `--color-surface-card`| `#FFFFFF` | `#1E293B` | Card, sheet, and elevated surfaces |
| `--color-surface-raised`| `#F1F5F9` | `#334155` | Secondary surface / subtle inputs |
| `--color-text-primary`| `#0F172A` | `#F8FAFC` | High-contrast body and headers |
| `--color-text-secondary`| `#475569` | `#94A3B8` | Metadata, timestamps, captions |
| `--color-text-muted` | `#94A3B8` | `#64748B` | Inactive placeholders, subtle borders |
| `--color-primary` | `#0284C7` (Sky 600) | `#38BDF8` (Sky 400) | Primary actions, branding, selected tabs |
| `--color-primary-light`| `#E0F2FE` (Sky 100) | `#082F49` (Sky 950) | Highlight pills, active state backgrounds |
| `--color-sage-accent` | `#059669` (Emerald 600) | `#34D399` (Emerald 400)| Health, verified medications, calm mood |
| `--color-amber-alert` | `#D97706` (Amber 600) | `#FBBF24` (Amber 400) | Schedule swap pending, tone friction warning |
| `--color-coral-critical`| `#E11D48` (Rose 600) | `#FB7185` (Rose 400) | Emergency medical alert, critical allergy badge |
| `--color-ai-glow` | `#8B5CF6` (Violet 500) | `#A78BFA` (Violet 400) | Peacekeeper suggestions, AI handoff badge |

### 2.2 Elevation & Border Radii
- **Radii System:**
  - `radius-sm`: `6px` (Badges, tags, miniature pills)
  - `radius-md`: `12px` (Standard inputs, buttons, calendar cells)
  - `radius-lg`: `18px` (Cards, dialog containers, quick intake bar)
  - `radius-xl`: `28px` (Floating action drawers, bottom sheets)
  - `radius-full`: `9999px` (Avatars, floating pills, circular buttons)
- **Shadow System (Soft Ambient Glow):**
  - `shadow-sm`: `0 1px 2px 0 rgba(0, 0, 0, 0.04)`
  - `shadow-md`: `0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.04)`
  - `shadow-lg`: `0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.03)`
  - `shadow-glow-ai`: `0 0 15px rgba(139, 92, 246, 0.25)`

---

## 3. Typography & Hierarchy

The typography pairs **Plus Jakarta Sans** (humanist, warm, legible geometric sans-serif for UI and text) with **JetBrains Mono** (for cryptographic hashes, time stamps, and dosage metrics).

| Scale Level | Font Family | Size / Line-Height | Weight | Tracking | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `display-lg` | Plus Jakarta Sans | `32px / 40px` | Bold (700) | `-0.02em` | App intro, celebratory milestones |
| `heading-1` | Plus Jakarta Sans | `24px / 32px` | SemiBold (600) | `-0.01em` | Screen titles ("Today's Feed", "Custody") |
| `heading-2` | Plus Jakarta Sans | `20px / 28px` | SemiBold (600) | `0em` | Section titles, card headers |
| `heading-3` | Plus Jakarta Sans | `17px / 24px` | Medium (500) | `0em` | Subsections, child profile names |
| `body-base` | Plus Jakarta Sans | `15px / 22px` | Regular (400) | `0em` | Chat messages, handoff notes, logs |
| `body-medium`| Plus Jakarta Sans | `15px / 22px` | Medium (500) | `0em` | Interactive list items, form labels |
| `caption` | Plus Jakarta Sans | `13px / 18px` | Regular (400) | `+0.01em` | Timestamps, secondary caregiver tags |
| `mono-code` | JetBrains Mono | `12px / 16px` | Regular (400) | `0em` | Medication doses, SHA-256 hashes, receipts |

---

## 4. Design System Component Library

### 4.1 Buttons & Interactive Controls
- **Primary Action Button:** Full-width or inline; background `--color-primary`; text white; subtle scale animation on tap (`transform: scale(0.98)`).
- **Secondary / Ghost Button:** Transparent background; border `1px solid var(--color-surface-raised)`; text `--color-text-primary`.
- **"Rewrite with Grace" Pill:** Floating pill button with subtle violet glow (`--color-ai-glow`); sparkling star icon (`Sparkles` from Lucide); single-tap triggers smooth inline transition.
- **Emergency SOS Quick Pill:** Permanently anchored in the top header; soft rose border and icon (`HeartPulse`); reveals offline-cached allergy, blood type, and emergency contacts with zero network delay.

### 4.2 Cards & Presentation Modules

#### A. Automated Handoff Summary Card
```
┌──────────────────────────────────────────────────────────────┐
│  ✨ Automated Handoff Briefing       [ 3:30 PM Shift Change ] │
│  For: Maya (Age 4) · Handing off to: David (Dad)             │
├──────────────────────────────────────────────────────────────┤
│  🥗 Nutrition: Lunch eaten (75%) · Water: 250ml              │
│  😴 Sleep: Nap 1:15 PM – 2:45 PM (1h 30m, restful)          │
│  💊 Meds: 2.5ml Zyrtec at 1:10 PM (by Maria - Verified 📸)   │
│  🎨 Mood & Play: Happy; painted a lion; mild sensory overload│
│     at 2:00 PM handled with weighted blanket (10 mins).      │
│  📌 Action Item: Pack yellow raincoat for tomorrow's field trip│
├──────────────────────────────────────────────────────────────┤
│  [ ✓ Acknowledge & Confirm Handoff ]    [ 💬 Ask Question ]  │
└──────────────────────────────────────────────────────────────┘
```

#### B. Custody Swap Request Card
```
┌──────────────────────────────────────────────────────────────┐
│  🔄 Schedule Swap Request                         [ PENDING ] │
│  From: Mark                                                  │
├──────────────────────────────────────────────────────────────┤
│  Proposed Trade:                                             │
│  • Mark takes Leo: Friday, Oct 17 (3:00 PM – Overnight)      │
│  • Elena receives in return: Saturday, Oct 25 (Full Day)     │
│                                                              │
│  Calendar Impact: No school conflict detected.               │
├──────────────────────────────────────────────────────────────┤
│  [ Accept Swap ]      [ Counter-Propose ]      [ Decline ]   │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Information Architecture & Navigation

### 5.1 Mobile Navigation Structure (5-Tab Anchor)
The mobile navigation maintains a fixed bottom tab bar with 5 primary views:

```
[ 🏠 Today ]   [ 📅 Calendar ]   [ 💬 Peacekeeper ]   [ 🩺 Health ]   [ 💳 Ledger ]
```

- **Top Bar Utility Strip:**
  - **Child Switcher Carousel:** Rounded chip selector to switch between siblings (e.g., `[👶 Maya (4)]`, `[👦 Leo (7)]`, `[All Children]`).
  - **Emergency Medical Quick-Pill:** Immediate access to offline emergency card.
  - **Caregiver Presence Pill:** Shows who is currently on active care duty ("Elena on duty until Friday 5 PM").

### 5.2 The Multimodal Quick-Intake Bar ("Action Dock")
Positioned floating directly above the bottom tab bar on the Today feed:
- **Microphone Icon (Hold to Record):** Instant audio waveform visualization; speech-to-text parsed directly into log cards.
- **Camera Icon (Snap & Log):** Instant OCR for school notes, artwork, medicine bottles, or lunch plates.
- **Quick Tap Icons:** One-tap logging for common events: `[🍼/🍽️ Meal]`, `[💤 Sleep]`, `[💊 Meds]`, `[💩 Potty]`, `[😊 Mood]`.

---

## 6. Screen Wireframes & Detailed User Flows

### 6.1 Screen 1: "Today" Dashboard & Daily Feed
```
┌──────────────────────────────────────────────────────────────┐
│ 👶 Maya · Active Caregiver: Maria (Nanny)     [ 🩺 Emergency ]│
├──────────────────────────────────────────────────────────────┤
│  Today, Tuesday Oct 14                                       │
│                                                              │
│  ┌─ ✨ NEXT UP: CUSTODY TRANSITION (5:00 PM) ───────────────┐ │
│  │  Handoff to Dad (David) in 1 hour 30 mins                │ │
│  │  [ View Draft Handoff Digest ]                           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  TIMELINE TODAY                                              │
│  • 1:15 PM  💊 Medication Logged                            │
│             Zyrtec 2.5ml given with water. Verified by Maria.│
│                                                              │
│  • 1:30 PM  😴 Nap Started                                  │
│             Fell asleep calmly with white noise machine.     │
│                                                              │
│  • 3:00 PM  ☀️ Nap Ended (1h 30m duration)                  │
│             Woke up cheerful. Snack: apple slices.           │
│                                                              │
│  [ 🎙️ Speak ] [ 📷 Scan ] [ 🍽️ Meal ] [ 💤 Nap ] [ 💊 Med ]   │
├──────────────────────────────────────────────────────────────┤
│ [ 🏠 Today ]  [ 📅 Calendar ]  [ 💬 Chat ]  [ 🩺 Health ] [ 💳 ]│
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Screen 2: Peacekeeper AI Messaging Screen
```
┌──────────────────────────────────────────────────────────────┐
│ < Back      💬 Co-Parent Chat: Elena & Mark      [ 🔒 Court ]│
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [ Elena · 2:15 PM ]                                         │
│  Can you make sure Leo brings his soccer cleats today?       │
│                                                              │
│  [ Mark · 2:20 PM ]                                          │
│  Already packed in his blue bag. Also gave his inhaler.      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  AI TONE ASSISTANT:                                          │
│  ┌─ ⚠️ TONE ALERT: Blame Detected ──────────────────────────┐ │
│  │  Your draft: "Why do you never check the bag yourself?"   │
│  │                                                          │
│  │  ✨ Suggested Rewrite:                                    │
│  │  "The cleats are already packed in the front zipper."    │
│  │                                                          │
│  │  [ ✨ Use Rewrite ]               [ Keep Original ]      │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  Type message...                                        [ ➤ ]│
└──────────────────────────────────────────────────────────────┘
```

### 6.3 Screen 3: Child Health & Emergency Quick-Card
```
┌──────────────────────────────────────────────────────────────┐
│ 🩺 Emergency Medical & Allergy Profile (OFFLINE READY)       │
├──────────────────────────────────────────────────────────────┤
│  CHILD: Maya Jenkins · DOB: 2022-04-12 (Age 4) · Blood: O+   │
│                                                              │
│  🚨 CRITICAL ALLERGIES:                                      │
│  • PEANUTS / TREE NUTS (Severe Anaphylaxis - Carries EpiPen)  │
│  • AMOXICILLIN (Mild Rash)                                   │
│                                                              │
│  💊 ACTIVE MEDICATIONS:                                      │
│  • Cetirizine (Zyrtec): 2.5ml once daily at 1:00 PM          │
│  • EpiPen Jr (0.15mg): Kept in backpack front pouch          │
│                                                              │
│  📞 EMERGENCY CONTACTS:                                      │
│  • Primary Pediatrician: Dr. Rachel Vance (555-019-2831)     │
│  • Mother (Elena): 555-014-9922                             │
│  • Father (Mark): 555-018-4411                              │
│  • Hospital of Choice: Children's Memorial (2.1 miles away)  │
│                                                              │
│  [ 📄 Export Pediatric Summary ]   [ 📋 Copy Info ]         │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. AI Interaction Patterns & Micro-Copy

### 7.1 Real-Time Tone Guidance Micro-Interactions
1. **Idle State:** Text input field contains a subtle neutral placeholder: *"Communicate with clarity and grace..."*
2. **Constructive Input:** A tiny green leaf icon illuminates with a calm tooltip: *"Tone: Clear & Constructive"*.
3. **Friction Detected:** The border smoothly transitions to a warm amber glow. A non-modal assistant card slides up above the keyboard with two side-by-side buttons: `[✨ Rewrite with Grace]` and `[Send As Is]`.
4. **Copywriting Guidelines for AI:**
   - **DO:** Say *"Here's a more direct and neutral way to phrase that:"*
   - **DON'T:** Say *"Your message is aggressive and violates parenting guidelines."*
   - **DO:** Highlight shared focus on the child: *"Keep the focus on Milo's schedule."*

### 7.2 Voice Quick-Logger Interaction
1. **Press and Hold:** Radial purple pulse radiates from microphone button.
2. **Speaking:** Waveform visualizer ripples in real-time with ambient haptic hum.
3. **Release:** Audio transcribed in $<400\text{ ms}$; floating preview card pops up:
   > *"Extracted: Maya took 5ml Motrin at 3:15 PM for mild fever (99.8°F). Add to medical log?"*
4. **Single-Tap Confirmation:** Confirms entry without requiring manual keyboard entry.

---

## 8. Accessibility, Haptics & Responsive Specs

### 8.1 Haptic Feedback Strategy (iOS & Android)
- **Selection Change:** Light impact haptic (`UIImpactFeedbackGenerator.light`) on switching child tabs or calendar days.
- **Successful Log / Acknowledgment:** Medium notification feedback (`UINotificationFeedbackGenerator.success`) on confirming a medication or approving a handoff digest.
- **Tone Alert Trigger:** Subtle double-tick warning haptic when inflammatory language is detected during typing.
- **Emergency Action:** Strong triple warning haptic on accessing or dialing emergency medical contacts.

### 8.2 Responsive Layout Guidelines
- **Mobile (320px – 480px):** Single-column layout with fixed bottom tabs and collapsible drawers.
- **Tablet (481px – 1024px):** Split-view master-detail pattern (e.g., calendar grid on left 60%, daily event log on right 40%).
- **Desktop Web (1025px+):** Three-pane layout: Left collapsible sidebar navigation, central feed/workspace, right persistent Child Quick-Health & Caregiver Presence panel.
