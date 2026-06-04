# 1. Setup GCP (una vez)
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
gcloud artifacts repositories create supermarket-analytics --repository-format=docker --location=us-central1

# 2. Deploy API
docker build -t us-central1-docker.pkg.dev/PROJECT/supermarket-analytics/supermarket-api:latest -f api/Dockerfile .
docker push us-central1-docker.pkg.dev/PROJECT/supermarket-analytics/supermarket-api:latest
gcloud run deploy supermarket-api --image ... --allow-unauthenticated --region us-central1

# 3. Deploy Frontend (con URL del API del paso anterior)
docker build --build-arg NEXT_PUBLIC_API_URL=https://supermarket-api-xxx.run.app -f frontend/Dockerfile frontend/
# push + deploy igual que el API