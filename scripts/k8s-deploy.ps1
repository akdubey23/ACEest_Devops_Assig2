param(
  [string]$Image = "docker.io/akanksha2402/aceest-fitness-api:v3.2.4",
  [string]$Namespace = "aceest",
  [string]$Strategy = "base"
)

$ErrorActionPreference = "Stop"

if ($Strategy -eq "base") {
  kubectl apply -k k8s/base
  kubectl -n $Namespace set image deployment/aceest-fitness-api aceest-fitness-api=$Image
  kubectl -n $Namespace rollout status deployment/aceest-fitness-api --timeout=120s
  kubectl -n $Namespace get svc aceest-fitness-api
  exit 0
}

$strategyFiles = @{
  "rolling" = "k8s/strategies/rolling-update.yaml"
  "blue-green" = "k8s/strategies/blue-green.yaml"
  "canary" = "k8s/strategies/canary.yaml"
  "shadow" = "k8s/strategies/shadow-deployment.yaml"
  "ab" = "k8s/strategies/ab-testing.yaml"
}

if (-not $strategyFiles.ContainsKey($Strategy)) {
  throw "Unknown strategy '$Strategy'. Use base, rolling, blue-green, canary, shadow, or ab."
}

kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f $strategyFiles[$Strategy]
kubectl -n $Namespace get pods,svc
