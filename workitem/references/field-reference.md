# Field reference

A **common set** of fields and values found in corporate issue trackers. It is not any single
product's schema — adapt it to the tool you use. Where your tracker's list differs, edit this
file; it is data, not code.

> **Only three fields are generated:** title, description and type. Priority, status, sprint,
> work package, due date and assignee are chosen by the user in the tracker, because they depend
> on the project and the team rather than on the work itself.
>
> **A value that is not on a list is never invented.** Output carries
> `SELECT: <field> — no match on the list, choose in the tracker` instead.

## TYPE

| Value | When |
|---|---|
| Task | General unit of work; the default when nothing else fits |
| Bug | Something that used to work is broken (a regression) |
| Defect | Built wrong or incomplete from the start; not a regression |
| Feature | New capability |
| Customer Requirement | A requirement stated by the customer (use the EARS form) |
| Software Requirement | A derived software requirement (use the EARS form) |
| Incident | An outage or failure experienced in production |
| Support | A request, question or assistance for a user or team |
| Improvement | Raising quality or speed of something that already works |
| Test | Test design or a verification run |
| Technical Debt | A deliberately deferred fix |
| Routine Work | Periodic or recurring maintenance |
| Change Request | A request to change scope or design |
| Field Work | Work carried out on site |
| Meeting | A meeting record |

For the two requirement types the description is written in the EARS form rather than as prose:
see `ears.md`.

## PRIORITY — chosen by the user

`Critical` · `High` · `Medium` · `Low` · `None`

## STATUS — chosen by the user

`To Do` · `In Progress` · `In Review` · `Test` · `Follow-up` · `Done`

Typical flow: `To Do` when the item is defined; `In Progress` once started; `In Review` or
`Test` while the work awaits verification; `Done` at closure. `/workitem-note` **suggests** a
closing status — a suggestion, not a selection.

## ESTIMATE

Many trackers attach the estimate to the **assignment**: adding a person reveals an estimate box
for that person, in hours. So the estimate is per assignee, and it only appears after someone is
assigned — the order is assign first, then enter the estimate.

Output gives a **range with its basis** rather than a bare number
(`3-5 h; six files touched, a comparable change took 4 h`). A bare figure reads as a measurement;
an estimate is not one.

Single-assignee assumption: with more than one assignee the split is the user's call.

## Note templates

| Template | Contents | Use for |
|---|---|---|
| Task note | Work done, completion criteria, notes | Task, Feature, Improvement, Bug |
| Test note | Test information plus a checklist table | Test, any verification run |
| Incident note | What/where/when, witnesses, impact, actions | Incident |
| Meeting minutes | Attendees, agenda, decisions, actions | Meeting |
| Blank page | Nothing | When none of the above fits |

Paste the **whole generated note into a blank page** rather than picking the tracker's own
template and filling cells one by one: a Markdown pipe table becomes a real table on paste, so
the result looks native and it is a single step.

## Fields the generator leaves empty

A field that is meaningful for the work but whose value the generator cannot know is **kept and
left blank**, never guessed: tested by, owner, start and target dates, reported by, witness
names and contacts, attendee names and units, minutes taker, time, location. Person names are
deliberately absent from this reference.

A section that is **not applicable** to the work (root cause on a new feature, dependencies when
there are none) is deleted instead — "none" is not written. A section that merely has nothing
to report yet is kept.

Blanks belong in table cells, which stay empty so the gap is visible on the page. Prose sections
get written; one with genuinely nothing in it may carry a single `…`, but not all of them — a
file whose prose is still the template word for word is the blank form, and `check` says so.
