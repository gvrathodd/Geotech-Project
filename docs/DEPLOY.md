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

## Optional: Google sign-in and saved projects (Firestore)

1. In Google Auth Platform, set up Branding and set the Audience to External (testing), adding
   the group's emails as test users. Under Clients, create a Web application client with the
   redirect URI `https://foundation-studio-237377681531.us-central1.run.app/oauth2callback`.
2. In Cloud Shell, inside the repo:

```bash
SA=237377681531-compute@developer.gserviceaccount.com
gcloud services enable firestore.googleapis.com secretmanager.googleapis.com
gcloud firestore databases create --location=us-central1
gcloud projects add-iam-policy-binding ce-402-project --member=serviceAccount:$SA --role=roles/datastore.user
cp deploy/secrets.toml.example secrets.toml && nano secrets.toml      # paste client id/secret + cookie secret
gcloud secrets create streamlit-secrets --data-file=secrets.toml && rm secrets.toml
gcloud secrets add-iam-policy-binding streamlit-secrets --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor
gcloud run deploy foundation-studio --source . --region us-central1 --allow-unauthenticated \
  --min-instances 0 --max-instances 1 --cpu 1 --memory 1Gi --timeout 900 --cpu-throttling \
  --set-secrets=/root/.streamlit/secrets.toml=streamlit-secrets:latest
```

Without the secret, the app runs in guest mode and hides saving.
