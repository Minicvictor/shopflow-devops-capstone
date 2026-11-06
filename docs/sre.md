# Site Reliability Engineering

## SLIs and SLOs
| Category | SLI | SLO (30 days) |
|---|---|---|
| Availability | Requests not returning HTTP 5xx / all requests | 99.5% |
| Latency | Requests answered in under 500 ms / all requests | 95% |

SLIs are measured from the backend `/metrics` endpoint by Prometheus recording rules
(`sli:availability:ratio_rate5m`, `sli:availability:ratio_rate1h`, `sli:latency_under_500ms:ratio_rate5m`).

## Error budget
- Availability: 100% - 99.5% = 0.5% of requests may fail.
- In time: 30 days x 24 h x 60 min = 43,200 min; 43,200 x 0.005 = **216 minutes** of full outage per 30 days.
- In requests: at 1,000,000 requests per 30 days, **5,000** failures are allowed.
- Latency: up to 5% of requests may be slower than 500 ms.
- Burn rate = (observed error ratio) / 0.005. A burn rate of 1 uses exactly the whole budget in 30 days.
- Alert `ErrorBudgetFastBurn` fires at a burn rate above 6 for 5 minutes.

## Error budget policy
| Budget remaining | Action |
|---|---|
| More than 50% | Normal feature work and releases |
| 10% to 50% | Releases need extra validation through the preview service |
| Less than 10% | Reliability work only; releases limited to fixes |
| Exhausted | Release freeze until the budget recovers; write a post-incident review |

## Incident severity levels
| Level | Definition | Example | Response target |
|---|---|---|---|
| SEV1 | Application fully down or data at risk | No backend endpoints, database unavailable | Acknowledge in 5 min, work until resolved |
| SEV2 | Major feature degraded or SLO burning fast | Error rate above 5%, p95 latency above 1 s | Acknowledge in 15 min |
| SEV3 | Minor problem with a workaround | One pod restarting, single alert flapping | Handle within the working day |
| SEV4 | Cosmetic or informational | Dashboard panel broken | Backlog |

## Ownership and on-call approach
- One **primary on-call** engineer and one **secondary** per week, rotating among team members.
- The primary acknowledges alerts, leads the response and communicates status.
- The secondary assists, takes over if the primary does not respond within 15 minutes, and takes notes.
- Each component has an owner who is the first call for it:

| Component | Owner |
|---|---|
| Backend and database | <team member> |
| Frontend and Kubernetes manifests | <team member> |
| CI/CD and GitOps | <team member> |
| Monitoring and logging | <team member> |

- Alerts route to Prometheus and the Grafana dashboard. A production setup would add Alertmanager with paging.

## Incident response steps
1. **Detect:** an alert fires, or someone reports a symptom.
2. **Acknowledge and classify:** assign a severity and an incident lead.
3. **Communicate:** post a short status (what is broken, who is working on it, next update time).
4. **Investigate:** check the Grafana dashboard, then pod status, then logs in Loki (see runbook).
5. **Mitigate first:** restore service before finding the full cause (roll back, restart, scale).
6. **Verify recovery:** health endpoints, dashboard, and a real request all succeed.
7. **Close:** announce recovery and record the timeline.

## Post-incident actions
- Write a short review within 2 working days using the template below.
- Blameless: focus on how the system allowed the failure, not who caused it.
- Every review lists corrective actions with an owner and a due date.
- Check how much error budget the incident consumed and apply the budget policy.

### Post-incident review template
| Field | Notes |
|---|---|
| Summary | |
| Severity | |
| Timeline (UTC+1) | |
| Symptom | |
| Detection | |
| Investigation | |
| Root cause | |
| Mitigation | |
| Recovery | |
| Prevention / action items (owner, date) | |
| Error budget consumed | |

## Known limitations
- Probe requests (`/health`, `/ready`) are counted in the request totals and slightly improve the availability figure.
- Prometheus retention is 2 days, so the 30-day SLO window cannot be calculated here; measurements use the available data.
- The latency threshold depends on the histogram bucket `le="0.5"` existing in the exporter.
