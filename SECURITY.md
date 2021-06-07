# Security Status

This file records the current state of the Snyk scan for this repository.

Last update: 7th June 2021

Project was removed from and re-added to Snyk to update manifests. Code Analysis was enabled.

| File | Issue | Snyk Severity | Commentary | Adjusted Serverity | Reviewed | Next Review | Action |
| ---- | ----- | ------------- | ---------- | ------------------ | -------- | ----------- | ------ |
| bootstrap_terraform.py | Jinja2 No Default Escape | Medium | Used at deployment time only. Would allow XSS if we had user input but as used currentl there is no obvious attack vector. | Low | 3-Jun-21 | 3-Dec-21 | Supress to focus on higher priority |
| adg_completion_status_sns.tf | SNS Topic Not Encrypted | Medium | No customer data is sent via these SNS topics, they are for job control only. | Low | 3-Jun-21 | 3-Dec-21 | Supress to focus on higher priority |
| pdm_cw_trigger_sns.tf | SNS Topic Not Encrypted | Medium | No customer data is sent via these SNS topics, they are for job control only. | Low | 3-Jun-21 | 3-Dec-21 | Supress to focus on higher priority |
| pom.xml | Snakeyaml DoS Vulnerability | Medium | This is pure DoS, and an internal, non-user facing endpoint | Low | 3-Jun-21 | 3-Dec-21 | Supress to focus on higher priority |

N.B. Due to limitations in Snyk, some vulnerabilties cannot be ignored through the snyk file, so the console has been used to ignore all for the time shown above.

N.B. We only consider medium and high vulnerabilties, lows are left.
