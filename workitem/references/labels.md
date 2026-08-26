# Label translations

Templates carry the canonical English labels. When the output language is not English the
section headings, table headers and pre-filled values are translated from this table, so wording
stays consistent across notes instead of being re-invented each time.

Add a column for another language and the templates keep working — this file is the only place
that needs touching.

> This map is read by `scripts/workitem_output.py` when it checks a note's structure, so it is
> data as well as documentation. Every label a template uses must appear here, and no Turkish
> string may map to two English labels — `tests/labels.py` fails if either breaks.

## Section headings

| English | Turkish |
|---|---|
| Purpose | Amaç |
| Scope | Kapsam |
| Out of Scope | Kapsam Dışı |
| Completion Criteria | Tamamlanma Kriterleri |
| Dependencies | Bağımlılıklar |
| Risks | Riskler |
| Work Done / Description | Yapılan İş / Açıklama |
| Notes | Notlar |
| Test Checklist | Test Kontrol Listesi |
| Findings / Notes | Bulgular / Notlar |
| Result | Sonuç |
| Description (what happened) | Açıklama (Ne yaşandı?) |
| Witnesses | Tanıklar |
| Impact / Outcome | Etki / Sonuç |
| Comments and Actions | Yorumlar ve Aksiyonlar |
| Attendees | Katılımcılar |
| Agenda | Gündem |
| Discussion and Decisions | Görüşülenler ve Kararlar |
| Actions | Aksiyonlar |
| Next Meeting | Sonraki Toplantı |

## Table and info labels

| English | Turkish |
|---|---|
| TESTED ITEM | TEST EDİLEN |
| VERSION | SÜRÜM / VERSİYON |
| ENVIRONMENT | ORTAM (ENVIRONMENT) |
| TESTED BY | TEST EDEN |
| DATE | TARİH |
| TASK | GÖREV |
| OWNER | SORUMLU |
| START | BAŞLANGIÇ |
| TARGET DATE | HEDEF TARİH |
| STATUS | DURUM |
| WHAT HAPPENED | NE OLDU (OLAY) |
| WHEN (DATE / TIME) | NE ZAMAN (TARİH / SAAT) |
| WHERE | NEREDE (YER) |
| SEVERITY | ÖNEM / ŞİDDET |
| REPORTED BY | RAPORLAYAN |
| SUBJECT | KONU |
| TIME | SAAT |
| LOCATION / PLATFORM | YER / PLATFORM |
| MINUTES BY | TUTANAĞI TUTAN |
| FULL NAME | AD SOYAD |
| CONTACT | İLETİŞİM |
| STATEMENT / NOTE | İFADE / NOT |
| UNIT / ROLE | BİRİM / ROL |
| ATTENDANCE | KATILIM |
| TEST STEP / SCENARIO | TEST ADIMI / SENARYO |
| EXPECTED RESULT | BEKLENEN SONUÇ |
| ACTUAL | GERÇEKLEŞEN |
| ACTION | AKSİYON |
| DUE | TERMİN |
| ESTIMATE | TAHMİN |
| ACTUAL HOURS | GERÇEKLEŞEN SAAT |
| VARIANCE | SAPMA |

## Tracker fields chosen by the user

These are not generated. The wording is needed because a work item file marks them for the
user to choose, and it has to name them the way the tracker shows them on screen.

| English | Turkish |
|---|---|
| PRIORITY | ÖNCELİK |
| STATUS | DURUM |
| SPRINT | SPRİNT |
| WORK PACKAGE | İŞ PAKETİ |
| ASSIGNEE | ATANANLAR |

## Work item file structure

| English | Turkish |
|---|---|
| Content for the tracker's New issue screen | Bu dosya tracker'daki Yeni Konu ekranına girilecek içeriktir |
| ► TITLE | ► KONU BAŞLIĞI |
| ► RIGHT PANEL FIELDS | ► SAĞ PANEL ALANLARI |
| ► DESCRIPTION (paste into the editor) | ► AÇIKLAMA (editöre yapıştır) |
| *select in the tracker* | *tracker'da seç* |
| *from you* | *senden* |
| **Estimate basis:** | **Tahminin dayanağı:** |
| TYPE | TİP |
| PARENT ISSUE | ÜST KONU |
| LABELS | ETİKETLER |
| SUB-TASK | ALT GÖREV |
| EK-<n> | EK-<n> |
| Detail annex for | Detay eki |
| ATTACHMENTS | EKLER |
| SPENT | HARCANAN |

## Paste format

Measured in one tracker (a ProseMirror/TipTap-family editor); re-measure in yours before trusting
it. Copied from a **rendered page** in a browser, the clipboard carries `text/html` and these all
arrive as themselves: `h1`-`h3`, `p`, `strong`, `em`, `s`, `code`, `hr`, `blockquote`, `table` with
`thead`, `ul`, `ol`, `li`. Copied from the **file**, the clipboard carries only `text/plain` and
the editor applies its own markdown rules instead — which convert headings, bold, lists and pipe
tables but **not** a checklist.

So a checklist is the one thing that decides the format. Six markdown syntaxes were tried
(`- [x]`, `* [x]`, bare `[x]`, `- [X]`, `+ [x]`, `1. [x]`) and every one arrived as a bullet with
a literal `[x]` next to it. What works, pasted as HTML:

```html
<ul data-type="taskList">
  <li data-type="taskItem" data-checked="true"><p>met</p></li>
  <li data-type="taskItem" data-checked="false"><p>not met</p></li>
</ul>
```

`data-checked` carries the state; a checked item is struck through by the editor, so no `<s>` is
added. A variant with `<label><input type="checkbox">` inside the item also works and is not
needed. Without the `data-type` attributes the list degrades to plain bullets.

Another tracker may want different markup. This table is where that changes.

## Date format

A date is written the way the output language writes it, not the way a database stores it.
The `--since` argument of `workitem_output.py commits` is a git input and stays ISO.

| English | Turkish |
|---|---|
| DD.MM.YYYY | GG.AA.YYYY |

## Values

| English | Turkish |
|---|---|
| ✅ Passed | ✅ Geçti |
| ⚠️ Partial | ⚠️ Kısmen |
| ❌ Failed | ❌ Kaldı |
| 🟪 Pending | 🟪 Bekliyor |
| ☐ Success | ☐ Başarılı |
| ☐ Failure | ☐ Başarısız |
| In progress | Devam ediyor |
| Attended | Katıldı |
| Open | Açık |
