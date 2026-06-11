# Apply Agent Lessons

These rules were migrated from the standalone `job_apply_agent` workflow and should remain part of the command center's auto-apply behavior.

## Hard Stops

- Stop on CAPTCHA, hCaptcha, reCAPTCHA, or "verify you are human" gates.
- Stop on OTP or verification-code requirements.
- Stop on forced account creation or login-only apply flows.
- Stop on unknown required legal, sponsorship, salary, or demographic questions.
- Never click final submit without explicit human approval.

## Reusable ATS Rules

- Lever application URLs usually append `/apply`.
- Ashby application URLs usually append `/application`.
- Greenhouse URLs vary; prefer the posting URL unless a form route is discovered.
- YC/company pages may hide the apply route; mark these `READY_FOR_REVIEW` instead of treating the page load as success.

## State Rules

- Use `READY_FOR_REVIEW` when safe fields were filled and the human must review before submit.
- Use `FILLED_PARTIALLY` when automation reached the form but could not complete enough known fields.
- Use `BLOCKED` for CAPTCHA, OTP, forced account creation, or automation errors.
- Use `SKIPPED` for closed roles or roles clearly outside the search criteria.

## Data Rules

- Treat `data/apply/candidate_profile.json` as the canonical autofill source.
- Do not infer missing legal or sponsorship answers from resume text.
- Keep `resume_master.pdf` local and ignored; only upload it when the form exposes a visible file input.
