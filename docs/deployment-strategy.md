# Deployment Strategy: Blue-Green

## Design
- Two backend Deployments, `backend-blue` and `backend-green`, run side by side.
- The `backend` Service selects the live slot by label (`version: blue|green`).
- The `backend-preview` Service points at the idle slot for validation.
- Slots use the Recreate strategy so a broken version can never hide behind old pods.
- Each slot has its own HPA. The PodDisruptionBudget covers all backend pods.
- Everything is deployed through Git and ArgoCD.

## Release procedure
1. Build the new image and set it on the **idle** slot only (never edit the live slot).
2. Merge. ArgoCD deploys it with no live traffic.
3. Validate through `backend-preview` (`/health`, `/ready`, `/api/products`, `/metrics`).
4. Flip the `# LIVE` and `# PREVIEW` selector labels in `k8s/backend-service.yaml` via PR.
5. Verify the endpoints of the `backend` Service and the app.
6. Keep the old slot running as the rollback target.

## Rollback
Revert the release PR in Git. ArgoCD syncs the Service selector back to the known-good slot.

## Test record
| Step | Result |
|---|---|
| New version (green 1.1.0) deployed, no traffic | OK |
| Validation via preview Service | passed |
| Traffic switched to green | OK |
| Deliberate failure: broken image 1.2.0-broken switched live | no endpoints, app down |
| Rollback by Git revert | traffic back on green, app recovered |

## Limitations
- Traffic moves 100% at once. A canary needs a replica ratio or a service mesh/Argo Rollouts.
- The live slot runs on the HPA minimum of one replica when idle. A production setup would keep two.
- Images are built into Minikube's Docker, so there is no registry.

