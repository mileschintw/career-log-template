---
title: Northwind Freight — Software Engineering Intern, Quotes team
type: internship
period: 2025-06 – 2025-09
org: Northwind Freight
my_role: Software Engineering Intern; owned the quote-latency fix and the invoice reconciler
collaborators: Priya (senior engineer, mentor) — co-designed the rollout; Sam (manager) — set the latency goal
tags: [go, python, postgresql, redis, kafka, feature-flags, latency]
visibility: public
links: [https://git.example.com/northwind/quotes, https://git.example.com/northwind/reconciler]
last_updated: 2025-10-02
---

# Northwind Freight — Software Engineering Intern, Quotes team

## One line
Cut the shipment-quote API's p95 latency from 820 ms to 210 ms and automated invoice reconciliation during a summer internship. (user, 2025-10-02)

## Context
- Northwind Freight's quote API answered sales and customer requests for shipping prices. Sales complained that quotes "spin" during calls. (user, 2025-10-02)
- The manager's goal for the summer: p95 under 300 ms before the autumn peak. (intern-goals doc, `sources/northwind/2025-06-goals.pdf` p.1)

## My contribution
- **I did:** profiled the quote path, found per-request rate lookups in PostgreSQL, built the Redis rate cache and its refresh job (PR #412); wrote the Kafka invoice reconciler in Go end to end. (PR #412; reconciler repo)
- **I led, with help from:** the rate cache's regional rollout, designed with Priya, who reviewed the flag plan and ran the first region's switch. (user, 2025-10-02)
- **Others did; I can explain it:** the quote engine's pricing rules (Sam's team); I read them to keep the cache keys correct. (user, 2025-10-02)

## How it works
- Rates change at most a few times a day, so a five-minute Redis cache with a background refresh replaces a PostgreSQL lookup on every request. A cache miss falls back to the database. (PR #412 description)
- The reconciler runs nightly: it consumes carrier invoice events from Kafka, matches each to a booked shipment, and flags mismatches above a tolerance for review. It replaced a manual spreadsheet check the finance team ran each week. (reconciler README; user, 2025-10-02)

## Decisions and trade-offs
| Decision | Options | Chosen | Why | In hindsight |
|---|---|---|---|---|
| Cache freshness | Invalidate on rate change / fixed TTL | Five-minute TTL plus refresh | No rate-change event existed; adding one meant touching another team's service (user, 2025-10-02) | Fine for rates; would not do for prices that change per minute |

## Dead ends and mistakes
- First suspected JSON serialisation; a profile showed it was under 5% of request time. Lost two days. (user, 2025-10-02)

## Results and evidence
| Metric | Value | How measured | Caveat | Source |
|---|---|---|---|---|
| Quote API p95 latency | 820 ms → 210 ms | Production dashboard, one week before vs one week after | Week after included a holiday with lower traffic | PR #412 comment; (user, 2025-10-02) |
| Invoices flagged by the reconciler | 3% of 40k per month (August 2025: 40,212 invoices) | Reconciler report, August 2025 | One month only | `reconciler@3f9c2a1:reports/2025-08.md:14` |
| Rate-cache rollout | Four sales regions over two weeks, zero rollbacks | Deploy log | — | (user, 2025-10-02) |

## People
- Priya said in the final review that the rollout plan "was the most careful one an intern has written here". (user, 2025-10-02)
- GAP: whether a return offer was made.

## Lessons
- Profile before guessing: the two lost days. (user, 2025-10-02)

## Likely questions
- *Why not invalidate the cache on rate change?* No event existed; see Decisions.
- *How did you know the latency gain was real and not the holiday?* GAP: whether the gain held in a normal-traffic week.

## Past phrasings
- **backend:** "Cut shipment-quote API p95 latency from 820 ms to 210 ms by replacing per-request PostgreSQL lookups with a Redis rate cache refreshed every five minutes" (examples/resume.tex)
- **backend:** "Built a Kafka consumer in Go that reconciles carrier invoices nightly, flagging 3% of 40k monthly invoices for review and removing a manual spreadsheet step" (examples/resume.tex)
- **backend:** "Co-designed a feature-flag rollout with a senior engineer, rolling out the new rate cache to all four sales regions over two weeks with zero rollbacks" (examples/resume.tex)

## Conflicts
- Settled: use "from 820 ms to 210 ms", not "5x faster" (820 / 210 is 3.9x). (sources/resumes/2025-09-draft.tex; PR #412 comment)

## Pending
