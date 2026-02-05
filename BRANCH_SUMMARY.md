# Branch Summary: Dashboard-Collection

**Base Branch:** `devel`  
**Commits:** 2  
**Files Changed:** 3 (all new files)  
**Lines Added:** 342

---

## Commits

| Hash | Message |
|------|---------|
| `a2789b4` | Add dashboard collectors for automation-reports integration |
| `0abc0de` | Refactor dashboard job template calculations for type consistency |

---

## Overview

This branch introduces a new **dashboard collectors module** for the metrics-utility library. The collectors provide SQL-based data collection from the AWX/Automation Controller database to support the automation-reports frontend dashboard.

---

## New Files

### 1. `metrics_utility/library/collectors/dashboard/__init__.py`
Module initialization that exports three collector functions:
- `dashboard_job_templates`
- `dashboard_top_projects`
- `dashboard_top_users`

### 2. `metrics_utility/library/collectors/dashboard/collectors.py` (197 lines)
Collector functions using the `@register` decorator pattern:

| Collector | Description |
|-----------|-------------|
| `dashboard_job_templates` | Collects job template summary data including run counts, success/failure rates, elapsed time, and cost calculations |
| `dashboard_top_projects` | Collects top projects by job execution count |
| `dashboard_top_users` | Collects top users by job execution count |

**Key Features:**
- Cost calculation logic (manual vs automated costs, savings)
- Elapsed time formatting (e.g., "2h 15m", "45m 30s")
- Type-safe numeric handling (Decimal → float/int conversion)
- JSON-serializable output matching automation-reports TypeScript interfaces

### 3. `metrics_utility/library/collectors/dashboard/queries.py` (128 lines)
SQL query definitions for AWX database:

| Function | Purpose |
|----------|---------|
| `get_job_template_summary_query()` | Aggregates job execution data per template |
| `get_top_projects_query()` | Placeholder query for top projects |
| `get_top_users_query()` | Placeholder query for top users |
| `format_elapsed_time()` | Converts seconds to human-readable format |

---

## Technical Details

- **Purpose:** Replace direct AWX API calls from the frontend with cached dashboard data collected by metrics-service
- **Database Tables Used:** `main_unifiedjob`, `main_unifiedjobtemplate`, `main_jobhostsummary`
- **Output Format:** JSON matching the automation-reports `Report` TypeScript interface
- **Cost Model:** $50/hour labor rate, $10/hour infrastructure rate
