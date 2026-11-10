pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('Syntax Check') {
            steps {
                sh 'python3 -m py_compile app.py'
                sh 'docker compose config -q'
            }
        }

        stage('Build Image') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Automated Deployment') {
            steps {
                sh 'docker compose up -d --remove-orphans'
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    for i in $(seq 1 15); do
                        if curl -fsS http://localhost:8081/health && \
                           curl -fsS -o /dev/null http://localhost:8081/; then
                            echo "Backend dan Frontend sehat"
                            exit 0
                        fi
                        echo "Menunggu aplikasi siap ($i/15)..."
                        sleep 2
                    done
                    echo "Health check GAGAL"
                    docker compose logs --tail=50
                    exit 1
                '''
            }
        }
    }

    post {
        success { echo 'Pipeline sukses: aplikasi Lab Inventory ter-deploy.' }
        failure { echo 'Pipeline gagal: cek log stage yang berwarna merah.' }
    }
}