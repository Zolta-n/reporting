# Report Style Guide

## Report Sections

The monthly report has 5 sections. Every entry must be categorized into **exactly one** section — the most appropriate one. Never place the same topic in more than one section.

| Section | Token | Content |
|---|---|---|
| Key Projects | `{{key_projects}}` | Neutral operational updates: ongoing projects, scheduled activities, process progress — use only if the item does not fit a more specific section below |
| What was good | `{{what_was_good}}` | Clearly positive outcomes: wins, confirmations, awards, above-target results |
| Market and Competition | `{{market_competition}}` | Market trends, competitor activity, pricing intelligence, external factors |
| What was less satisfactory | `{{less_satisfactory}}` | Clearly negative or risky items: delays, unresolved issues, forecast reductions, lost opportunities, operational risks |
| News | `{{news}}` | Announcements, new partnerships, upcoming events, structural or organisational changes |

## Categorization Rules

Use sentiment to assign each entry to the correct section:

- **Positive** (win, confirmation, award, above-target) → **What was good**
- **Negative or risky** (delay, unresolved risk, reduction, lost opportunity) → **What was less satisfactory**
- **Market / competitor** intelligence → **Market and Competition**
- **Announcement / event / structural change** → **News**
- **Neutral operational** (ongoing project, scheduled visit, process update) → **Key Projects** — only if the item does not qualify for any of the above

## Categorization Examples

| Entry type | Correct section |
|---|---|
| Customer project nomination confirmed, nomination letter received | What was good |
| Volume transfer from plant closure remains unconfirmed, creating operational risk | What was less satisfactory |
| Customer significantly reduced an already-confirmed forecast with unclear reasoning | What was less satisfactory |
| Process audit or hobbing visit scheduled at customer site | Key Projects |
| Account scoring framework development underway | Key Projects |
| VA/VE project added to regular PMO review | Key Projects |
| Best Quality Award received | What was good |
| New customer partnership agreement signed | News |
| Competitor launched a new product in our segment | Market and Competition |

## Formatting
- Each distinct topic or project is its own paragraph (a separate string in the JSON array)
- Do not use bullet points, dashes, or numbered lists
- Keep each paragraph to 1-2 short sentences maximum

## Language and Tone
- Executive, neutral, factual language only
- Do not mention any individual person's name (first name, last name, or title of a specific person)
- You may mention customer names, company names, product names, and business unit names
- Avoid hedging language ("it seems", "perhaps", "might"); state facts directly
- Quantify outcomes where possible (volumes, percentages, budget figures, timelines)

## What to Omit
- Email greetings, signatures, and metadata (From:, Date:, Subject:)
- Internal procedural commentary ("as we discussed", "please find attached")
- Personal opinions or informal language
- Information without clear business relevance
