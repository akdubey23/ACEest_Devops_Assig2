// ACEest Fitness API — simple CI-style pipeline for coursework
// Works on Windows Jenkins (bat) and Linux agents (sh).
// Windows: scripts/jenkins-windows-ci.cmd finds Python (service account has no user PATH).
// Optional: set job/node env PYTHON_JENKINS=C:\Path\to\python.exe if discovery still fails.

pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
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

        stage('Docker build') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'docker build -t aceest-fitness-api:jenkins .'
                        sh 'docker tag aceest-fitness-api:jenkins aceest-fitness-api:staging'
                    } else {
                        bat 'docker build -t aceest-fitness-api:jenkins .'
                        bat 'docker tag aceest-fitness-api:jenkins aceest-fitness-api:staging'
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
    }

    post {
        always {
            junit testResults: 'test-results/junit.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'test-results/*.html,allure-results/**/*', allowEmptyArchive: true, fingerprint: true
        }
    }
}
