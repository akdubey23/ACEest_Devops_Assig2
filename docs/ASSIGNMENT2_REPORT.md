# ACEest Fitness & Gym - Assignment 2 CI/CD Report

## 1. Architecture Overview

ACEest Fitness & Gym uses the Assignment 1 Flask API as the application baseline from `https://github.com/akdubey23/ACEest_Devops`. The Assignment 2 repository is `https://github.com/akdubey23/ACEest_Devops_Assig2`. The API is implemented in `app.py`, persists data with SQLite, and exposes routes for programs, clients, workouts, analytics, PDF/CSV reporting, authentication, AI-style program generation, and membership status.

The Assignment 2 CI/CD architecture is:

1. Developer pushes changes to GitHub.
2. Jenkins polls the Git repository and checks out the latest commit.
3. Jenkins installs Python dependencies from `requirements.txt`.
4. Pytest runs unit/e2e tests and produces JUnit, HTML, Allure, and coverage reports.
5. SonarQube analysis runs when Jenkins is configured with a SonarQube server and scanner.
6. Docker builds a test image and executes tests inside the container build.
7. Docker builds the runtime image.
8. Jenkins runs a short-lived staging container and smoke-tests `/health`.
9. Jenkins optionally pushes versioned images to Docker Hub.
10. Jenkins optionally deploys the image to Kubernetes/Minikube using the manifests in `k8s/`.

GitHub Actions mirrors the core CI path for repository visibility: dependency installation, syntax check, Pytest, report upload, SonarQube scan when secrets are configured, Docker test image build, runtime image build, and optional Docker Hub push from `main`.

## 2. Tools and Dependencies

Application dependencies are captured in `requirements.txt`:

- Flask for the web API.
- Pytest for automated testing.
- pytest-cov for coverage output consumed by SonarQube.
- fpdf2 for PDF report generation.
- allure-pytest and pytest-html for CI evidence reports.

External tools required on the Jenkins/DevOps machine:

- Git and a GitHub repository.
- Python 3.10+.
- Jenkins with Pipeline, Git, JUnit, Docker Pipeline, and SonarQube Scanner plugins.
- Docker Desktop or Docker Engine.
- SonarQube server and `sonar-scanner`.
- Docker Hub account and access token.
- Minikube and kubectl for local Kubernetes deployment.

## 3. Deployment Strategies

Kubernetes manifests are provided under `k8s/`:

- `k8s/base/` deploys the normal rolling-update application with a NodePort service.
- `k8s/strategies/rolling-update.yaml` demonstrates zero-downtime rolling update settings.
- `k8s/strategies/blue-green.yaml` runs blue and green deployments. Rollback is done by switching the service selector back to the last stable color.
- `k8s/strategies/canary.yaml` runs four stable pods and one canary pod behind one service for approximate weighted exposure.
- `k8s/strategies/shadow-deployment.yaml` runs primary and shadow workloads. True traffic mirroring requires an ingress controller or service mesh, so this manifest provides the Kubernetes workload base.
- `k8s/strategies/ab-testing.yaml` runs two variants behind separate services. Header/user routing requires an ingress controller, API gateway, or service mesh.

Rollback examples:

```bash
kubectl -n aceest rollout undo deployment/aceest-fitness-api
kubectl -n aceest rollout status deployment/aceest-fitness-api
```

Blue/green rollback:

```bash
kubectl -n aceest patch service aceest-blue-green -p '{"spec":{"selector":{"app":"aceest-fitness-api","color":"blue"}}}'
```

## 4. Manual Setup Required

Some Assignment 2 requirements depend on external accounts or local services and cannot be fully automated from the repository alone.

1. Create or use a public GitHub repository and push this project.
2. In Jenkins, configure SCM polling or use the included `pollSCM` trigger in `Jenkinsfile`.
3. Install Docker and ensure the Jenkins agent can run `docker`.
4. Create Docker Hub credentials in Jenkins with id `dockerhub-credentials`.
5. Replace `akanksha2402/aceest-fitness-api` in `Jenkinsfile` and Kubernetes YAML files with your real Docker Hub repository.
6. Configure SonarQube in Jenkins with server name `SonarQube`; then set `SONARQUBE_ENABLED=true` for the Jenkins job.
7. For GitHub Actions SonarQube and Docker push, add repository secrets: `SONAR_HOST_URL`, `SONAR_TOKEN`, `DOCKERHUB_USERNAME`, and `DOCKERHUB_TOKEN`.
8. Start Minikube before deployment:

```bash
minikube start
kubectl apply -k k8s/base
minikube service aceest-fitness-api -n aceest
```

## 5. Key Automation Outcomes

The repository now supports automated dependency installation, repeatable Pytest runs, CI test reporting, coverage generation, SonarQube analysis configuration, Docker container testing, runtime image builds, staging smoke tests, optional Docker Hub publishing, and Kubernetes deployment manifests for multiple progressive delivery patterns.

The main challenges are environment-specific: Jenkins service accounts on Windows often lack Python and Docker PATH access, SonarQube requires server/plugin configuration, Docker Hub requires credentials, and advanced shadow/A-B routing requires ingress or service-mesh support beyond plain Kubernetes services.
