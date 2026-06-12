# Apply input templates

The auto-apply lane reads its inputs from `data/apply/` (override with
`APPLY_INPUT_DIR`). That folder is gitignored because it holds personal data.
To set up a fresh machine, copy these templates and fill them in:

```bash
mkdir -p data/apply
cp examples/apply/candidate_profile.example.json data/apply/candidate_profile.json
cp examples/apply/qa.example.json data/apply/qa.json
cp examples/apply/constraints.example.json data/apply/constraints.json
# also place your resume at data/apply/resume_master.pdf
```

| File | Used for |
| --- | --- |
| `candidate_profile.json` | Contact fields, links, and checkbox/radio answers the runner may fill. |
| `qa.json` | Reusable answers to common free-text questions (human reference). |
| `constraints.json` | Policy stops and preferences for which jobs to attempt. |
| `resume_master.pdf` | Uploaded when a form has a visible resume input. |

The runner only fills a field when a profile value confidently matches it, skips
demographic/legal questions, stops on CAPTCHA/OTP/forced account creation, and
**never clicks final submit**. Every attempt writes a review folder under
`data/apply/reviews/` and a row to the `application_attempts` table.
