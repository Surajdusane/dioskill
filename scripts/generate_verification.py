#!/usr/bin/env python3
"""
Employment verification JSON generator.

Reads a JSON blob of raw candidate details and produces the formatted
verification JSON (company code, dates avoiding Sundays, salary figures,
payslip month, etc).

Usage:
    python3 generate_verification.py input.json
    (or pipe JSON on stdin)
"""
import json
import sys
import datetime as dt

TODAY = dt.date.today()

# ---------------------------------------------------------------------------
# Company code mapping
# ---------------------------------------------------------------------------
# base code -> full company name (lowercased, for matching)
COMPANY_BASE = {
    "asc": "ascloudsecure",
    "kas": "kasper analitics",
    "car": "carrigrow",
    "pre": "precesion stafficng",
    "rcm": "precise rcm healthcare",
    "ga1": "globla a1 rcm",
}
# companies that get a "-noi" (or similar) variant when the role is
# Technical Support. Only asc and kas have documented variants.
NOI_VARIANT = {
    "asc": "ascnoi",
    "kas": "kasnoi",
}


def is_technical_support(designation: str) -> bool:
    d = (designation or "").lower()
    return "technical support" in d or " tse" in d or d.strip() == "tse"


def resolve_company_code(last_company: str, designation: str) -> str:
    lc = (last_company or "").lower().strip()
    base_code = ""
    for code, full_name in COMPANY_BASE.items():
        if full_name in lc or lc in full_name or lc == code:
            base_code = code
            break
    if not base_code:
        return ""
    if is_technical_support(designation) and base_code in NOI_VARIANT:
        return NOI_VARIANT[base_code]
    return base_code


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def parse_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s}")


def fmt(d):
    return d.strftime("%Y-%m-%d") if d else ""


def avoid_sunday(d: dt.date, prefer_forward=True) -> dt.date:
    """If date falls on Sunday, bump it by one day (forward by default,
    otherwise backward)."""
    if d.weekday() == 6:  # Sunday == 6
        return d + dt.timedelta(days=1 if prefer_forward else -1)
    return d


def add_months(d: dt.date, months: int) -> dt.date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return dt.date(year, month, day)


def pick_near_6(year: int, month: int) -> dt.date:
    """Day 6 of the given month; if that's a Sunday, use the 7th instead.
    (Confirmed against real examples: increment letters land on the 6th,
    except when the 6th is a Sunday, in which case they shift to the 7th.)"""
    candidate = dt.date(year, month, 6)
    if candidate.weekday() == 6:
        candidate = dt.date(year, month, 7)
    return candidate


# ---------------------------------------------------------------------------
# Salary helper
# ---------------------------------------------------------------------------
def monthly_from_annual(annual: float) -> int:
    """Convert an annual CTC figure to a monthly figure, floored to the
    nearest 10 (matches the reference example: 350000 -> 29160)."""
    monthly = annual / 12.0
    return int(monthly // 10) * 10


def years_of_experience(join: dt.date, leave: dt.date) -> float:
    return (leave - join).days / 365.25


# ---------------------------------------------------------------------------
# Main transform
# ---------------------------------------------------------------------------
def build_record(raw: dict) -> dict:
    name = raw.get("name", "").strip()
    phone = raw.get("phone_number", "") or raw.get("number", "")
    last_company = raw.get("last_company", "") or raw.get("company", "")
    designation = raw.get("designation", "")
    join_date = parse_date(raw.get("joining_date") or raw.get("date_of_joining"))
    leave_date = parse_date(raw.get("relieving_date") or raw.get("date_of_releiving"))
    last_salary = raw.get("last_in_hand_salary") or raw.get("last_salary")
    pan = raw.get("pan", "")
    bank_no = raw.get("bank_account", "") or raw.get("account_no", "")
    email = raw.get("email", "")
    employee_id = raw.get("employee_id", "")  # left blank unless supplied
    gender = (raw.get("gender") or "").lower()

    company_name = resolve_company_code(last_company, designation)

    # --- dates -------------------------------------------------------
    joining_date = avoid_sunday(join_date) if join_date else None
    last_working_date = avoid_sunday(leave_date) if leave_date else None
    release_date = last_working_date

    offer_date = None
    if joining_date:
        offer_date = avoid_sunday(joining_date - dt.timedelta(days=7), prefer_forward=False)

    email_date = None
    if release_date:
        email_date = avoid_sunday(release_date - dt.timedelta(days=30), prefer_forward=False)

    increment_letter_date = increment_effective_date = None
    if joining_date and last_working_date:
        # The increment letter always falls in the SAME MONTH as joining,
        # on the 6th (7th if the 6th is a Sunday). Confirmed across all
        # reference examples. What's NOT determinable from dates alone is
        # *which* anniversary year to use: two employees with near-identical
        # tenure (~29 months) landed on different anniversaries (1yr vs 2yr),
        # so the count of increments actually granted must be supplied
        # explicitly rather than guessed from tenure length.
        increments_given = raw.get("increments_given")
        if increments_given is None:
            # Fallback guess only if not supplied: full years elapsed,
            # minimum 1. Flag this to the user - it is not guaranteed correct.
            months_elapsed = (last_working_date.year - joining_date.year) * 12 + \
                (last_working_date.month - joining_date.month) - \
                (1 if last_working_date.day < joining_date.day else 0)
            increments_given = max(1, months_elapsed // 12)
        anniv_year = joining_date.year + int(increments_given)
        increment_letter_date = pick_near_6(anniv_year, joining_date.month)
        increment_effective_date = increment_letter_date

    # --- payslip month -------------------------------------------------
    payslip_month = ""
    if last_working_date:
        next_month_num = last_working_date.month + 1
        next_month_year = last_working_date.year + (1 if next_month_num > 12 else 0)
        next_month_num = next_month_num if next_month_num <= 12 else next_month_num - 12
        tenth_of_next_month = dt.date(next_month_year, next_month_num, 10)
        if tenth_of_next_month < TODAY:
            payslip_month = next_month_num + 1 if next_month_num < 12 else 1
        else:
            payslip_month = next_month_num

    # --- salary ----------------------------------------------------
    initial_salary = payslip_amount = increment_amount = ""
    if last_salary:
        try:
            annual = float(last_salary)
            initial_salary = payslip_amount = increment_amount = monthly_from_annual(annual)
        except ValueError:
            pass

    # --- gender flag -------------------------------------------------
    x_flag = ""
    if gender.startswith("m"):
        x_flag = "is"
    elif gender.startswith("f"):
        x_flag = "er"

    return {
        "company_name": company_name,
        "name": name,
        "employee_id": employee_id,
        "designation": designation.lower() if designation else "",
        "pan_no": pan,
        "bank_no": bank_no,
        "initial_salary": initial_salary,
        "payslip_ammount": payslip_amount,
        "increment_amount": increment_amount,
        "email_id": email,
        "phone_number": phone,
        "offer_date": fmt(offer_date),
        "joining_date": fmt(joining_date),
        "increment_letter_date": fmt(increment_letter_date),
        "increment_effective_date": fmt(increment_effective_date),
        "last_working_date": fmt(last_working_date),
        "release_date": fmt(release_date),
        "email_date": fmt(email_date),
        "payslip_month": payslip_month,
        "x": x_flag,
    }


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)
    print(json.dumps(build_record(raw), indent=4))


if __name__ == "__main__":
    main()
