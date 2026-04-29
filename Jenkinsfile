// ACEest Fitness API - Assignment 2 CI/CD pipeline.
// Works on Windows Jenkins (bat) and Linux agents (sh).
// Manual Jenkins setup before enabling optional stages:
// - SonarQube Scanner + SonarQube server named SONARQUBE_ENV (default: "SonarQube")
// - Docker Hub username/repository in DOCKERHUB_IMAGE and credentials id in DOCKERHUB_CREDENTIALS_ID
// - kubectl context pointing at Minikube/Kubernetes before KUBE_DEPLOY_ENABLED=true

pipeline {
    agent any

    triggers {
        pollSCM('H/5 * * * *')
    }

    options {
        skipDefaultCheckout(true)
    }

    parameters {
        booleanParam(name: 'SONARQUBE_ENABLED', defaultValue: true, description: 'Run SonarQube analysis and enforce the quality gate')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: true, description: 'Push the Jenkins-built image tags to Docker Hub')
        booleanParam(name: 'KUBE_DEPLOY_ENABLED', defaultValue: true, description: 'Deploy the pushed image to Kubernetes')
        string(name: 'SONARQUBE_ENV', defaultValue: 'SonarQube', description: 'Jenkins SonarQube server configuration name')
        string(name: 'SONAR_SCANNER_TOOL', defaultValue: 'SonarScanner', description: 'Jenkins SonarQube Scanner tool installation name')
        string(name: 'DOCKERHUB_IMAGE', defaultValue: 'akanksha2402/aceest-fitness-api', description: 'Docker Hub image repository')
        string(name: 'DOCKERHUB_CREDENTIALS_ID', defaultValue: 'dockerhub-credentials', description: 'Jenkins Docker Hub credentials ID')
        string(name: 'KUBECONFIG_PATH', defaultValue: 'C:\\Users\\Akanksha\\.kube\\config', description: 'Kubeconfig path available to the Jenkins Windows service')
        string(name: 'KUBE_NAMESPACE', defaultValue: 'aceest', description: 'Kubernetes namespace for optional deployment')
    }

    environment {
        APP_NAME = 'aceest-fitness-api'
        LOCAL_IMAGE = 'aceest-fitness-api'
        DOCKERHUB_IMAGE = "${params.DOCKERHUB_IMAGE ?: 'akanksha2402/aceest-fitness-api'}"
        DOCKERHUB_CREDENTIALS_ID = "${params.DOCKERHUB_CREDENTIALS_ID ?: 'dockerhub-credentials'}"
        PUSH_IMAGE = "${params.PUSH_IMAGE ?: false}"
        SONARQUBE_ENABLED = "${params.SONARQUBE_ENABLED ?: false}"
        SONARQUBE_ENV = "${params.SONARQUBE_ENV ?: 'SonarQube'}"
        SONAR_SCANNER_TOOL = "${params.SONAR_SCANNER_TOOL ?: 'SonarScanner'}"
        KUBE_DEPLOY_ENABLED = "${params.KUBE_DEPLOY_ENABLED ?: false}"
        KUBECONFIG = "${params.KUBECONFIG_PATH ?: 'C:\\Users\\Akanksha\\.kube\\config'}"
        KUBE_NAMESPACE = "${params.KUBE_NAMESPACE ?: 'aceest'}"
    }

    stages {
        stage('Checkout') {
            steps {
                retry(3) {
                    checkout scm
                }
            }
        }

        stage('Install dependencies') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m pip install --upgrade pip'
                        sh 'python3 -m pip install -r requirements.txt'
                    } else {
                        bat 'call scripts\\jenkins-windows-ci.cmd install'
                    }
                }
            }
        }

        stage('Test') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            mkdir -p test-results allure-results
                            python3 -m pytest tests/ -v --tb=short \\
                              --junitxml=test-results/junit.xml \\
                              --alluredir=allure-results \\
                              --cov=app --cov-report=xml:test-results/coverage.xml \\
                              --html=test-results/pytest-report.html --self-contained-html
                            PYEXIT=$?
                            python3 scripts/build_test_dashboard.py || true
                            exit $PYEXIT
                        '''
                    } else {
                        bat 'call scripts\\jenkins-windows-ci.cmd test'
                    }
                }
            }
        }

        stage('SonarQube analysis') {
            when {
                expression { return env.SONARQUBE_ENABLED == 'true' }
            }
            steps {
                script {
                    def scannerHome = tool "${env.SONAR_SCANNER_TOOL}"
                    withSonarQubeEnv("${env.SONARQUBE_ENV}") {
                        if (isUnix()) {
                            sh "${scannerHome}/bin/sonar-scanner"
                        } else {
                            bat "\"${scannerHome}\\bin\\sonar-scanner.bat\""
                        }
                    }
                }
            }
        }

        stage('SonarQube quality gate') {
            when {
                expression { return env.SONARQUBE_ENABLED == 'true' }
            }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Containerized tests') {
            steps {
                script {
                    if (isUnix()) {
                        sh "docker build --target test -t ${env.LOCAL_IMAGE}:test ."
                    } else {
                        bat "docker build --target test -t %LOCAL_IMAGE%:test ."
                    }
                }
            }
        }

        stage('Docker build') {
            steps {
                script {
                    if (isUnix()) {
                        sh "docker build --target runtime -t ${env.LOCAL_IMAGE}:jenkins -t ${env.LOCAL_IMAGE}:staging -t ${env.DOCKERHUB_IMAGE}:${env.BUILD_NUMBER} -t ${env.DOCKERHUB_IMAGE}:latest ."
                    } else {
                        bat "docker build --target runtime -t %LOCAL_IMAGE%:jenkins -t %LOCAL_IMAGE%:staging -t %DOCKERHUB_IMAGE%:%BUILD_NUMBER% -t %DOCKERHUB_IMAGE%:latest ."
                    }
                }
            }
        }

        // Staging: run image like a short-lived staging env, smoke-test /health, tear down.
        // Uses host port 5099 -> container 5000 (change STAGING_HOST_PORT if Jenkins already uses 5099).
        stage('Staging') {
            environment {
                STAGING_NAME = 'aceest-staging-jenkins'
                STAGING_HOST_PORT = '5099'
            }
            steps {
                script {
                    if (isUnix()) {
                        sh """
                            docker rm -f ${env.STAGING_NAME} 2>/dev/null || true
                            docker run -d --name ${env.STAGING_NAME} -p ${env.STAGING_HOST_PORT}:5000 aceest-fitness-api:staging
                            cleanup() { docker rm -f ${env.STAGING_NAME} 2>/dev/null || true; }
                            trap cleanup EXIT
                            ok=0
                            for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
                              if curl -sf "http://127.0.0.1:${env.STAGING_HOST_PORT}/health" | grep -q ok; then
                                ok=1
                                break
                              fi
                              sleep 2
                            done
                            if [ "\$ok" != "1" ]; then
                              echo "Staging smoke test failed: /health did not return ok in time"
                              exit 1
                            fi
                            echo "Staging health check passed:"
                            curl -s "http://127.0.0.1:${env.STAGING_HOST_PORT}/health"
                        """
                    } else {
                        bat 'call scripts\\jenkins-windows-staging.cmd'
                    }
                }
            }
        }

        stage('Push Docker image') {
            when {
                expression { return env.PUSH_IMAGE == 'true' }
            }
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDENTIALS_ID, usernameVariable: 'DOCKERHUB_USERNAME', passwordVariable: 'DOCKERHUB_PASSWORD')]) {
                        if (isUnix()) {
                            sh 'echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin'
                            sh "docker push ${env.DOCKERHUB_IMAGE}:${env.BUILD_NUMBER}"
                            sh "docker push ${env.DOCKERHUB_IMAGE}:latest"
                            sh 'docker logout || true'
                        } else {
                            bat 'echo %DOCKERHUB_PASSWORD% | docker login -u %DOCKERHUB_USERNAME% --password-stdin'
                            bat "docker push %DOCKERHUB_IMAGE%:%BUILD_NUMBER%"
                            bat "docker push %DOCKERHUB_IMAGE%:latest"
                            bat 'docker logout'
                        }
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            when {
                expression { return env.KUBE_DEPLOY_ENABLED == 'true' }
            }
            steps {
                script {
                    if (isUnix()) {
                        sh """
                            kubectl apply -k k8s/base
                            kubectl -n ${env.KUBE_NAMESPACE} set image deployment/${env.APP_NAME} ${env.APP_NAME}=${env.DOCKERHUB_IMAGE}:${env.BUILD_NUMBER}
                            kubectl -n ${env.KUBE_NAMESPACE} rollout status deployment/${env.APP_NAME} --timeout=120s
                        """
                    } else {
                        bat 'kubectl apply -k k8s/base'
                        bat "kubectl -n %KUBE_NAMESPACE% set image deployment/%APP_NAME% %APP_NAME%=%DOCKERHUB_IMAGE%:%BUILD_NUMBER%"
                        bat "kubectl -n %KUBE_NAMESPACE% rollout status deployment/%APP_NAME% --timeout=120s"
                    }
                }
            }
        }
    }

    post {
        always {
            junit testResults: 'test-results/junit.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'test-results/*.html,test-results/*.xml,allure-results/**/*', allowEmptyArchive: true, fingerprint: true
        }
    }
}
