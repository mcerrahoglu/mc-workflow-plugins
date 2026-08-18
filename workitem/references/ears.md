# EARS patterns (for requirement-typed items)

When TYPE is **Customer Requirement** or **Software Requirement**, the description is written in
the EARS form rather than as prose. Some trackers offer an EARS helper in the editor; if yours
inserts a different skeleton, compare it with the set below and edit this file to match.

## The five patterns

**1. Ubiquitous** — always in force, no trigger.
```
The <system> shall <response>.
```
*The system shall record a SHA-256 digest of every uploaded document.*

**2. Event-driven** — when a specific event occurs.
```
When <trigger>, the <system> shall <response>.
```
*When a user uploads a document, the system shall not begin processing before the virus scan
completes.*

**3. State-driven** — while a state holds.
```
While <state>, the <system> shall <response>.
```
*While maintenance mode is enabled, the system shall answer every request with 503.*

**4. Unwanted behaviour** — the error path.
```
If <unwanted condition>, then the <system> shall <response>.
```
*If the virus scanning service is unreachable, then the system shall reject the document.*

**5. Optional feature** — only where the capability exists.
```
Where <feature is present>, the <system> shall <response>.
```
*Where a GPU is present, the system shall extract tables with the accelerated parser.*

**Complex** — a combination (`While ... When ... the ... shall ...`). Split it where possible;
chaining two conditions in one requirement costs more in readability than it saves.

## Writing rules

- **One requirement per item.** If an "and" or "or" asks for two things, write two requirements.
- **Be measurable.** Not "shall be fast" but "shall respond within 500 ms".
- **State the need, not the solution.** Which library implements it is design, not requirement.
- **`shall` means mandatory.** Keep `should`/`may` for optional behaviour; in a tracker the
  obligation is usually also carried by the priority field.
- **Language independence:** the pattern is built in whichever language the text is written in.
  Do not mix two languages in one requirement.
