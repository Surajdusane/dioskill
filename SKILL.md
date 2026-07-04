---
name: dioskill
description: Formats raw employee/candidate details (name, phone, last company, designation, joining/relieving dates, salary, PAN, bank account, email, reference contact) into the standardized employment-verification JSON used for offer letters, increment letters, and relieving/payslip records. Use this whenever the user provides candidate details for background/employment verification and wants the structured JSON output with computed company code, salary figures, and Sunday-safe dates (offer date, joining date, increment letter/effective date, last working/release date, email date, payslip month).
---

# Employment Verification Formatter

Converts raw candidate input into the standardized verification JSON. Because
the date math and salary math are rule-based and easy to get wrong by hand,
always run `scripts/generate_verification.py` rather than computing fields
manually.

## Workflow

1. Collect the raw fields from the user's message. Required-if-available:
   `name`, `phone_number`, `last_company`, `designation`, `date_of_joining`,
   `date_of_releiving`, `last_in_hand_salary`, `pan`, `bank_account`, `email`,
   `gender` (male/female — used for the trailing `x` flag; leave unset if
   unclear about the name), `increments_given` (how many increment cycles
   the person has actually received — see note below, ask the user if not
   obviously stated).
2. Write these into a JSON file (dates in `DD/MM/YYYY` or `YYYY-MM-DD`).
3. Run:
   ```
   python3 scripts/generate_verification.py input.json
   ```
4. Return the printed JSON to the user as-is.

## Rules implemented by the script

- **company_name**: derived from `last_company` + whether `designation`
  contains "technical support". Base codes: `asc`=ASCLOUDSECURE,
  `kas`=Kasper Analitics, `car`=Carrigrow, `pre`=Precesion Stafficng,
  `rcm`=Precise RCM Healthcare, `ga1`=Global A1 RCM. `asc`/`kas` get a `noi`
  suffix (`ascnoi`/`kasnoi`) when the role is Technical Support.
- **employee_id**: left blank (`""`) unless explicitly supplied — do not
  invent one.
- **Salary** (`initial_salary`, `payslip_ammount`, `increment_amount`):
  `last_in_hand_salary` is treated as an annual figure, divided by 12, and
  floored to the nearest 10 (e.g. 350000 → 29160). Note: this script
  currently only handles the "short tenure / single figure" case. If you
  need the multi-step increment ladder (for candidates with 2+ years'
  experience, where the joining salary steps up through 2–3 increments
  before landing on the final figure), that logic is not yet encoded —
  confirm the step amounts with the user before hand-computing it.
- **Dates**, all computed to avoid landing on a Sunday:
  - `joining_date` = as given (bumped off Sunday if needed).
  - `offer_date` = joining date − 7 days.
  - `last_working_date` / `release_date` = relieving date as given.
  - `email_date` = release date − 30 days.
  - `increment_letter_date` / `increment_effective_date` = **same month as
    joining_date**, on the 6th — or the 7th if the 6th is a Sunday. The
    *year* is `joining_date.year + increments_given` (e.g. 1 increment given
    → next year, same month; 2 increments given → two years later, same
    month). Confirmed exactly against 8 real reference records.
  - **`increments_given` is required input, not derivable from dates.**
    Two employees with near-identical tenure (~29 months) had different
    increment counts (1 vs 2) — tenure length does not reliably predict this,
    so ask the user for it. If genuinely not provided, the script falls back
    to `floor(tenure_months / 12)` (minimum 1) as a rough guess, but flag
    to the user that this is unverified.
- **payslip_month**: take the month after `last_working_date`; check whether
  the 10th of that month is still in the future relative to today. If it has
  already passed, use the month after that instead.
- **x**: `"is"` if gender is male, `"er"` if female, blank if unknown/unclear.

## Known open questions

These parts of the original spec were ambiguous and are NOT fully encoded —
flag them to the user rather than guessing silently:
- The multi-increment salary ladder for 2+ years of experience (exact step
  amounts). Reference examples show `initial_salary` (at joining),
  `payslip_ammount` (current, pre-latest-increment), and `increment_amount`
  (post-latest-increment) can all differ, but the raw last-in-hand-salary
  inputs behind those examples weren't available, so the conversion formula
  from a raw salary figure to these three numbers is still unconfirmed
  beyond the simple "annual/12, floor to 10" single-figure case.
- The `noi` suffix (`ascnoi`/`kasnoi`) does NOT purely follow the designation
  text. Example: "Technical Recruiter" at Kasper got `kasnoi`, but the same
  title "Technical Recruiter" at ASCLOUDSECURE did not get `ascnoi`. Only
  literal "Technical Support Engineer" roles are confirmed to reliably
  trigger the `noi` variant (for both `asc` and `kas`). For any other title,
  ask the user directly whether the `noi` variant applies rather than
  guessing from the title alone.
- The full set of company/designation variants beyond `ascnoi`/`kasnoi`
  (e.g. `kasnoitse`, `kastse`) — meanings not yet confirmed.
