# Frontend layout optimization and UX improvements

This is a frontend-only follow-up to the [visual refinements](ui-refinements.md).
The earlier uncommitted changes were preserved. A source/test snapshot was taken
before this increment to distinguish its changes from the earlier work.

## Layout changes

- Simplified the authenticated header to the sidebar toggle, ALEX branding, New Chat,
  and sign-out. It stays compact at a single height instead of using a second row
  for feature destinations. The unauthenticated layout remains the existing auth screen.
- Moved Ask Alex, Documents, and Research into the sidebar in that order, using the
  existing `activeTab` state and handlers. Research remains disabled and labelled Soon.
- Kept conversation creation, selection, history pagination, timestamps, rename and
  confirmed deletion below primary navigation. The history list scrolls independently.
- Added a desktop collapsed icon rail with accessible labels, native tooltips, active
  indicators and an expand control. Mobile uses a dismissible modal drawer with
  focus containment, an explicit close action and inert background controls.
- Sidebar expansion is view-only state. It does not reset the conversation or draft,
  and it is not persisted into authentication/conversation storage. Crossing the
  desktop breakpoint establishes the appropriate expanded/drawer default.
- Kept the file picker inside the composer and retained the existing Documents-view
  uploader. No upload action was added to the header or sidebar. Attachment chips
  are width-bounded, wrap, and have a bounded scroll area.
- Anchored the composer through flex layout inside the chat panel, not fixed to the
  browser window. The message region owns scrolling; the composer does not overlay it.
  Added safe-area spacing and visual-viewport resize handling for smaller usable
  viewports. The workspace's temporary body scroll lock is restored when it unmounts.

## Additional UX improvements

- A Jump to latest control appears when the reader is more than 96px from the end.
  New answers do not force readers away from earlier content. Users at the bottom
  continue following new content. Prepending older history preserves the visible
  offset; each newly opened conversation starts at its latest exchange.
- Copy response uses the actual assistant text. Code-copy controls use the same small
  reusable component. Success/error announcements follow the clipboard promise and
  timers are cleaned up. Clipboard rejection offers manual text selection.
- Failed requests offer Reload conversation through the existing history-read path.
  There is no dedicated backend regeneration/idempotent retry API, so no unsupported
  retry action or automatic paid-generation retry was added.
- Existing source references and safe Markdown rendering remain intact. No citation
  metadata is fabricated, HTML remains escaped, and unsafe URL schemes stay blocked.
- Added shared inline status presentation and confirmed-success notices for creation,
  rename, deletion, and ready uploads. A FAILED/PROCESSING upload cannot become a ready
  attachment or change the active document scope. Existing error/dialog recovery remains.
- Added the discoverable unmodified `N` shortcut for new conversations outside editable
  fields. It ignores modifiers, composition, repeat, handled events, editable controls
  and open dialogs. Native dialog Escape and mobile drawer Escape remain available.

## Files changed in this increment

| File | Change |
| --- | --- |
| `frontend/src/App.jsx` | Sidebar navigation wiring, viewport/focus handling, feedback and composer structure |
| `frontend/src/components/Header.jsx` | Compact essential actions and background inertness |
| `frontend/src/components/ConversationSidebar.jsx` | Navigation sections, collapsed rail and drawer accessibility |
| `frontend/src/components/WorkspaceNavigation.jsx` | Shared expanded/collapsed feature destinations |
| `frontend/src/components/Chat.jsx` | Independent message region, reading position and Jump to latest |
| `frontend/src/components/ChatInput.jsx` | Composer padding and bounded attachment layout |
| `frontend/src/components/ChatMessage.jsx` | Response copy and supported reload recovery |
| `frontend/src/components/MessageContent.jsx` | Shared code-copy component |
| `frontend/src/components/CopyButton.jsx` | Accessible clipboard feedback and cleanup |
| `frontend/src/components/InlineStatus.jsx` | Reusable dismissible inline feedback |
| `frontend/src/state/conversationWorkspace.js` | Confirmed notices and upload-readiness feedback |
| `frontend/src/utils/workspaceLayout.js` | Tested scroll policy and shortcut eligibility |
| `frontend/src/index.css` | Header/rail/navigation, dock, scrolling, status and safe-area styles |
| `frontend/index.html` | Mobile viewport/safe-area metadata |
| `frontend/tests/components.test.js` | Server-rendered JSX layout, semantics and escaping checks |
| `frontend/tests/workspaceLayout.test.js` | Scroll anchoring/follow policy and safe shortcuts |
| `frontend/tests/conversationWorkspace.test.js` | Notice timing, failed uploads and duplicate submission regressions |
| `docs/ui-refinements.md` | Pointer from the preceding styling report |
| `docs/frontend-layout-optimization.md` | This report |

The backend, schema, API service, package dependencies, lockfile, environment templates,
Vercel configuration and backend deployment configuration were not changed. Previous
memory, authentication, owner isolation, conversation persistence and stale-response
guards continue to use the existing infrastructure.

## Commands and verification

| Check | Actual result |
| --- | --- |
| `npm ls --depth=0 --prefix frontend` | Inspected installed React 18.3.1, Vite 5.4.21, Tailwind 3.4.19 and existing dependencies |
| `npm --prefix frontend test` | **50 tests passed**, 0 failed, 0 skipped |
| `npm --prefix frontend run build` | Passed with the existing Vite production build |
| `git diff --check` | Passed |
| `npm --prefix frontend run` | Confirmed no lint or type-check scripts exist; these checks are unavailable |
| Component rendering | Seven tests compile JSX with the existing Vite toolchain and render actual React components to static markup without browser/HTTP access |
| Browser verification | Not completed: browser access to the localhost preview was declined by the permission policy |

The 50 tests include all 32 preceding API/controller/formatting cases, five additional
controller regressions, six scroll/shortcut policy cases, and seven component-rendering
cases. Component checks cover header/navigation placement, active/disabled destinations,
collapsed labels, mobile modal semantics, composer controls, actual citation metadata,
copy/reload controls and HTML escaping. These tests do not prove browser geometry,
clipboard permissions, focus behavior or hardware keyboard behavior.

The existing local API and Vite servers were started with a synthetic, temporary SQLite
fixture and mocked AI/embeddings. The browser permission denial occurred before any
new UI interaction. No alternate browser, origin or automation workaround was attempted.
The temporary servers were then stopped. Application data and live AI credentials
were not used. No new screenshot or interactive console-error result is claimed.

## Remaining verification and limitations

Interactive checks at 360px, 390px, 768px, 1280px and 1440px remain pending. This includes
actual drawer/collapse/focus behavior, copy actions, long-history scrolling, message
arrival while reading, document attachment layout, console errors and mobile soft-keyboard
behavior. CSS and unit policies were checked, but browser interaction is not represented
as a completed test. Earlier screenshots show the prior layout, not this increment.

The application remains light-theme-only. Research, streaming and backend regeneration
remain unavailable. No new migrations or deployment steps are required for this layout
increment. No commit, push or deployment was performed.
