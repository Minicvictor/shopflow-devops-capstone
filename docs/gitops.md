# GitOps with ArgoCD

## Design
- ArgoCD runs in the `argocd` namespace on Minikube.
- Desired state lives in Git: `k8s/` on the `main` branch.
- The ArgoCD Application is defined in `gitops/argocd-app.yaml`.
- Automated sync with prune and self-heal.
- The backend Deployment's replica count is ignored in diffs because the HPA manages it.
- Secrets are not stored in Git. `shopflow-secret` is created from `.env` at deploy time.

## Workflow
1. Change a manifest on a branch.
2. Open a pull request, CI runs, merge to `main`.
3. ArgoCD detects the change and syncs the cluster.

## Drift detection
Scaled the frontend to 3 replicas with kubectl. ArgoCD showed OutOfSync and the diff, and a sync restored 1 replica from Git.

## Rollback
Changed frontend replicas to 2 through a PR, then reverted the PR. ArgoCD synced the revert and the cluster returned to the previous state.

## Limitations
- Secrets are bootstrapped manually. A production setup would use Sealed Secrets or an external secrets operator.
- ArgoCD polls Git every 3 minutes unless a webhook is configured.

