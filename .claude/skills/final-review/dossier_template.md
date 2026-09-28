# Dossier template

The layout of the final-review page. Edit the wording, order or rules here and
the next run follows them. Each `## section:` block is one part of the page;
`config.json` → `sections` picks which are written and in what order. Text in
`{braces}` is filled in; lines starting with `>>` are instructions to Claude
and are not copied to the page.

## section: frontmatter

```
---
title: {course title} final review
type: analysis
created: {today}
updated: {today}
tags: [{course tags}, final-review]
---

# {course title} final review

*Written by Claude on {today} from your quiz attempts and the wiki. Every fix
links the wiki heading that states it and the source file behind that heading.*
```

## section: snapshot

```
## Where you stand

{exam line}. {n} items: {counts by status}.
```
>> One table: Item (link), status, latest score (add "solid" where it applies),
>> points to review. Same order as the steps.

## section: plan

```
## Plan
```
>> A numbered, timed plan for the time left before the exam: which steps to do
>> first, when to retake which quiz sets, when to stop. Keep it to 4–7 lines.
>> Weak items first, then shaky, then a last pass over "Numbers to know".

## section: steps

>> One step per item, in worklist order. Skip items with nothing to review.
>> Heading: `## Step {k}: {item title} ({status}, latest {score})`.
>> Then these parts, in order:

```
**What went wrong.** {one or two sentences naming the pattern across the misses,
not a list of question numbers}

{one block per point:}
- **{short claim, as you should now say it}.** You {chose X / left it blank /
  reasoned "..."}; the answer is {Y} because {reason}. {wiki heading link} ·
  {source file link}
```
>> Claim first, in plain words, as a fact to learn. Quote the user's own
>> reasoning only when it shows the misconception, and keep it short.
>> Every point gets two links: the wiki heading that states the fact (check the
>> heading candidates by reading them; use the item's concept page when it has
>> the fact, else the page that does) and the source file behind that page
>> (a lecture deck, reading, textbook chapter or GSI set), as a vault link from
>> the worklist's "Sources behind this item". If only the GSI key states it,
>> link [[<GSI set page>]] and its PDF.
>> Points of kind "fixed" go in one closing line: "Fixed since: ...".

```
**Review.**
- [ ] {source to reread, with what to look for}
**Then.** {which quiz set to take next for this item, by its label}
```

## section: patterns

```
## Patterns across items
```
>> 3–5 bullets on habits that cost marks across items (blank reasons, "see
>> lecture" as a reason, mixing up two terms). Each names the items it hit.

## section: numbers

```
## Numbers to know cold
```
>> Every figure, cut-off or percentage behind a missed point, one line each with
>> its link. Only figures the wiki does not mark as disputed.

## section: untested

```
## Not yet tested
```
>> Items with no attempts: what they cover in one line, their wiki page, and the
>> quiz set to take. Leave the section out if there are none.

## section: sources

```
## Sources
```
>> Every source file linked above, once, grouped as lecture decks, readings,
>> textbook, discussion and practice sets, then the wiki pages. Ends with the
>> usual Related list: the mastery page, dashboard, pre-test and post-test banks.
