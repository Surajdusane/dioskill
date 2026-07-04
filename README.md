# dioskill

A Claude Skill that formats raw employee/candidate details into a standardized
employment-verification JSON (offer letters, increment letters, relieving
records, payslip data).

## What it does

Given raw candidate fields (name, phone, last company, designation, joining
and relieving dates, salary, PAN, bank account, email), it produces a
structured JSON record with:

- A resolved company code (e.g. `asc`, `ascnoi`, `kas`, `kasnoi`, `car`,
  `pre`, `rcm`, `ga1`)
- Sunday-safe computed dates: offer date, joining date, increment letter /
  effective date, last working / release date, email date
- Salary figures and payslip month

## Usage

Install this as a Claude Skill (drop the folder into your skills directory,
or upload the packaged `.skill` file in claude.ai / Claude Code / Cowork).
Once installed, just describe a candidate's details and ask for the
verification JSON — Claude will invoke:

```
python3 scripts/generate_verification.py input.json
```

See `SKILL.md` for the full rule set and known open questions.

## Status

Core date logic (offer date, joining date, increment anniversary, release
date, email date, payslip month) is verified against real reference records.
Two things still require explicit input rather than being auto-derived:

- `increments_given` — how many increment cycles the employee has received
  (not reliably predictable from tenure length alone)
- Whether the `noi` company-code suffix applies for titles other than
  "Technical Support Engineer"

See the "Known open questions" section in `SKILL.md` for details.
