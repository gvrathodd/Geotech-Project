# Deployment (Google Cloud Run, free tier)

In Google Cloud Shell:

```bash
git clone https://github.com/gvrathodd/Geotech-Project.git && cd Geotech-Project
gcloud run deploy foundation-studio --source . --region us-central1 --allow-unauthenticated \
  --min-instances 0 --max-instances 1 --cpu 1 --memory 1Gi --timeout 900 --cpu-throttling
gcloud artifacts repositories set-cleanup-policies cloud-run-source-deploy \
  --location us-central1 --policy deploy/cleanup-policy.json
```

The service scales to zero when idle and can never run more than one instance. CPU is billed
only during requests, and the cleanup policy keeps only the newest images. Also set a budget
alert under Billing → Budgets & alerts. To update the deployment, run `git pull`, then the same
`gcloud run deploy` command.
