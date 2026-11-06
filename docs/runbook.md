# Incident Runbook

Every scenario follows: **symptom → detection → investigation → root cause → mitigation → recovery → prevention**.
Replace `NS` with `shopflow`. Backend traffic is served by the `backend` Service, which selects the blue or green slot.

## First five minutes (any incident)
```bash
kubectl get pods -n shopflow -L version
kubectl get endpoints backend -n shopflow
kubectl get events -n shopflow --sort-by=.lastTimestamp | tail -15
curl http://localhost:5000/health        # with the backend port-forward running
```
Then open Grafana → ShopFlow Overview and note when the graphs changed.

## Scenario 1: Backend down (SEV1)
- **Symptom:** page cannot load products; `curl /health` fails.
- **Detection:** `BackendDown` alert, empty endpoints for `backend`.
- **Investigation:** `kubectl get pods -n shopflow -L version`, then `kubectl describe pod <pod>` and `kubectl logs <pod> --previous`.
- **Common root causes:** bad image, crash on start, database unreachable, Service selecting the wrong slot.
- **Mitigation:** if a recent release caused it, revert the release PR in Git and let ArgoCD sync (blue-green switch back). Do not edit the cluster by hand, because self-heal will undo it.
- **Recovery check:** endpoints list pod IPs, `/ready` returns 200, ArgoCD shows Healthy.
- **Prevention:** validate on `backend-preview` before switching traffic.

## Scenario 2: Database unavailable (SEV1)
- **Symptom:** API returns 5xx, backend `/ready` fails.
- **Detection:** `HighErrorRate`, `PodNotReady`, errors in Loki: `{namespace="shopflow", app="backend"} |~ "(?i)error|refused|timeout"`.
- **Investigation:** `kubectl get pods -n shopflow -l app=postgres`, `kubectl logs -n shopflow -l app=postgres --tail 30`, `kubectl get pvc -n shopflow`.
- **Mitigation:** if the pod is gone or crashed, `kubectl delete pod -n shopflow -l app=postgres` (it is recreated). If scaled to 0 by mistake, scale it back to 1. Data lives on the PVC, so it survives a pod restart.
- **Recovery check:** postgres pod Running, backend `/ready` returns 200, `GET /api/products` returns the data.
- **Prevention:** keep the PVC, alert on `PodNotReady`, document who may scale the database.

## Scenario 3: High error rate or latency (SEV2)
- **Symptom:** slow responses or a growing share of 5xx.
- **Detection:** `HighErrorRate`, `HighLatencyP95`, `ErrorBudgetFastBurn`.
- **Investigation:** Grafana CPU and memory panels, `kubectl top pods -n shopflow`, `kubectl get hpa -n shopflow`, error logs in Loki.
- **Mitigation:** if CPU is saturated, confirm the HPA is scaling (or raise the slot's replicas through Git). If a release started it, roll back.
- **Recovery check:** p95 under 1 s, error ratio below 1%, burn rate alert resolved.
- **Prevention:** load test before release, review resource limits.

## Scenario 4: Pod crash loop (SEV3)
- **Symptom:** a pod shows `CrashLoopBackOff` or high restart count.
- **Detection:** `PodRestartingFrequently`.
- **Investigation:** `kubectl logs <pod> --previous`, `kubectl describe pod <pod>` (look for OOMKilled).
- **Mitigation:** raise the memory limit through Git if OOMKilled, or revert the change that broke startup.
- **Prevention:** probes with sensible delays, resource limits based on observed usage.

## Rollback procedure
1. Find the release PR in GitHub (`git log --oneline -10`).
2. Click **Revert** on the PR and merge the revert PR.
3. Force a sync: `kubectl annotate application shopflow -n argocd argocd.argoproj.io/refresh=hard --overwrite`.
4. Verify: `kubectl get endpoints backend -n shopflow`, then restart the port-forward and call `/health`.

## After the incident
Fill in the post-incident review template in `docs/sre.md` within 2 working days.

