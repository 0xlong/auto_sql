# AWS App Runner Deployment Guide for Auto SQL

This guide explains how to deploy your Auto SQL Streamlit application to AWS App Runner, step by step, from first principles.

## Table of Contents
1. [Understanding AWS App Runner](#understanding-aws-app-runner)
2. [Prerequisites](#prerequisites)
3. [Preparing Your Application](#preparing-your-application)
4. [Setting Up AWS Account](#setting-up-aws-account)
5. [Deploying to AWS App Runner](#deploying-to-aws-app-runner)
6. [Configuring Environment Variables](#configuring-environment-variables)
7. [Accessing Your Deployed App](#accessing-your-deployed-app)
8. [Troubleshooting](#troubleshooting)

---

## Understanding AWS App Runner

### What is AWS App Runner?

**AWS App Runner** is a fully managed service that automatically builds, deploys, and runs containerized web applications. Think of it like this:

- **Your local machine**: You run `streamlit run src/app.py` and access it at `localhost:8501`
- **AWS App Runner**: AWS runs your app in the cloud and gives you a public URL like `https://yourapp.awsapprunner.com`

### How It Works (First Principles)

1. **Containerization**: Your app is packaged into a Docker container (a self-contained environment with your code, dependencies, and runtime)
2. **Build Process**: AWS App Runner reads your `Dockerfile` (instructions for building the container) and creates an image
3. **Deployment**: AWS runs your container on their servers
4. **Scaling**: AWS automatically handles traffic - if many people use your app, it scales up; if fewer people use it, it scales down
5. **Management**: AWS handles updates, monitoring, and health checks automatically

### Why Use AWS App Runner?

- **No server management**: You don't need to configure servers, install software, or manage infrastructure
- **Automatic scaling**: Handles traffic spikes automatically
- **Easy deployments**: Push code to Git, and AWS automatically deploys it
- **Cost-effective**: Pay only for what you use (starts around $5-10/month for low traffic)

---

## Prerequisites

Before deploying, ensure you have:

### 1. **AWS Account**
   - Sign up at [aws.amazon.com](https://aws.amazon.com)
   - You'll need a credit card (AWS has a free tier, but requires a card)
   - Free tier includes 750 hours/month of App Runner for 12 months

### 2. **GitHub Account** (or GitLab/Bitbucket)
   - Your code needs to be in a Git repository
   - AWS App Runner connects to your repository and deploys from there

### 3. **Your Application Ready**
   - Code committed to Git repository
   - `Dockerfile` created (already done for you)
   - Environment variables documented (credentials needed)

### 4. **AWS CLI** (Optional but Recommended)
   - Download from [aws.amazon.com/cli](https://aws.amazon.com/cli)
   - Allows you to manage AWS from command line
   - Not required - you can do everything in the AWS Console (web interface)

---

## Preparing Your Application

### Step 1: Push Your Code to GitHub

1. **Create a GitHub repository** (if you haven't already):
   - Go to [github.com](https://github.com)
   - Click "New repository"
   - Name it (e.g., "auto-sql")
   - Make it **public** (App Runner free tier supports public repos) or **private** (requires AWS connection setup)

2. **Push your code**:
   ```powershell
   # Navigate to your project directory
   cd C:\Users\Longin\Desktop\Projects\auto_sql

   # Initialize git (if not already done)
   git init

   # Add all files (except those in .gitignore)
   git add .

   # Commit your code
   git commit -m "Initial commit - ready for AWS App Runner deployment"

   # Add your GitHub repository as remote (replace YOUR_USERNAME and YOUR_REPO)
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

   # Push to GitHub
   git branch -M main
   git push -u origin main
   ```

### Step 2: Verify Required Files

Ensure these files exist in your repository:
- ✅ `Dockerfile` (already created)
- ✅ `requirements.txt` (already exists)
- ✅ `src/app.py` (your main application)
- ✅ `apprunner.yaml` (optional configuration file, already created)
- ✅ `.dockerignore` (excludes unnecessary files, already created)

---

## Setting Up AWS Account

### Step 1: Create AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click "Create an AWS Account"
3. Follow the signup process (requires email, password, credit card)
4. Verify your email and phone number

### Step 2: Access AWS Console

1. Go to [console.aws.amazon.com](https://console.aws.amazon.com)
2. Sign in with your credentials
3. You'll see the AWS Management Console dashboard

### Step 3: Choose AWS Region

**Important**: Choose a region close to your users for better performance.

1. In the top-right corner, click the region dropdown
2. Select a region (e.g., `us-east-1` for US East, `eu-west-1` for Europe)
3. **Remember this region** - you'll deploy your app here

---

## Deploying to AWS App Runner

### Method 1: Using AWS Console (Web Interface) - Recommended for First Time

#### Step 1: Navigate to App Runner

1. In AWS Console, search for "App Runner" in the search bar
2. Click on "App Runner" service
3. Click "Create service" button

#### Step 2: Configure Source

**Source type**: Choose "Source code repository"

1. **Connect to GitHub** (first time only):
   - Click "Add new" next to "Connection"
   - Click "Connect to GitHub"
   - Authorize AWS to access your GitHub account
   - Give the connection a name (e.g., "my-github-connection")
   - Click "Connect"

2. **Select Repository**:
   - Choose your repository from the dropdown
   - Select the branch (usually "main" or "master")
   - Deployment trigger: "Automatic" (deploys on every push) or "Manual" (you trigger deployments)

#### Step 3: Configure Build

**Build type**: Choose "Docker"

1. **Dockerfile path**: `Dockerfile` (default, already correct)
2. **Docker build context**: Leave empty (defaults to repository root)
3. **Build command**: Leave empty (Dockerfile handles this)
4. **Start command**: Leave empty (Dockerfile CMD handles this)

#### Step 4: Configure Service

1. **Service name**: `auto-sql` (or any name you prefer)
2. **Virtual CPU**: `0.25 vCPU` (sufficient for low traffic, cheaper)
3. **Memory**: `0.5 GB` (sufficient for Streamlit app)
4. **Auto scaling**:
   - Min instances: `1` (always keep 1 running)
   - Max instances: `5` (scale up to 5 if traffic increases)

#### Step 5: Configure Network

1. **Ingress**: "Public" (allows internet access)
2. **VPC**: Leave default (unless you need private networking)

#### Step 6: Configure Environment Variables

**This is critical for your app to work!**

Click "Add environment variable" and add:

1. **GOOGLE_LLM_API_KEY**:
   - Key: `GOOGLE_LLM_API_KEY`
   - Value: Your Google AI API key (from your `.env` file)

2. **GOOGLE_BIGQUERY_CREDENTIALS**:
   - Key: `GOOGLE_BIGQUERY_CREDENTIALS`
   - Value: Your entire BigQuery service account JSON as a **single-line string**
     - Open your service account JSON file
     - Copy the entire JSON content
     - Remove all line breaks and spaces (or keep it as-is, but ensure it's one continuous string)
     - Paste it here

**Important**: The `GOOGLE_BIGQUERY_CREDENTIALS` must be the entire JSON object as a string. For example:
```
{"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",...}
```

#### Step 7: Review and Create

1. Review all settings
2. Click "Create & deploy"
3. AWS will now:
   - Pull your code from GitHub
   - Build the Docker image using your Dockerfile
   - Deploy the container
   - This takes 5-10 minutes the first time

#### Step 8: Monitor Deployment

1. You'll see a deployment progress screen
2. Status will show: "Creating" → "Running"
3. Once "Running", your app is live!

---

## Configuring Environment Variables

### Why Environment Variables?

Your app needs credentials (API keys, BigQuery credentials) to work. Instead of hardcoding them (which is insecure), we use environment variables. AWS App Runner injects these into your container at runtime.

### How to Add/Update Environment Variables

1. Go to AWS App Runner console
2. Click on your service name
3. Go to "Configuration" tab
4. Click "Edit" next to "Environment variables"
5. Add or modify variables
6. Click "Save changes"
7. AWS will automatically redeploy with new variables

### Security Best Practices

- ✅ **Never commit credentials to Git** (they're in `.gitignore`)
- ✅ **Use AWS App Runner environment variables** for secrets
- ✅ **Rotate keys regularly** (change them periodically)
- ✅ **Use AWS Secrets Manager** (advanced) for sensitive data

---

## Accessing Your Deployed App

### Finding Your App URL

1. In AWS App Runner console, click your service
2. At the top, you'll see "Default domain"
3. It looks like: `https://xxxxx.us-east-1.awsapprunner.com`
4. Click the URL to open your app in a browser

### Custom Domain (Optional)

You can use your own domain (e.g., `auto-sql.yourdomain.com`):

1. In your service, go to "Custom domains" tab
2. Click "Add domain"
3. Follow the instructions to verify domain ownership
4. AWS will provide DNS records to add to your domain registrar

---

## Troubleshooting

### Common Issues and Solutions

#### 1. **Build Fails**

**Symptoms**: Deployment shows "Failed" status

**Solutions**:
- Check build logs in AWS Console → Your service → "Logs" tab
- Verify `Dockerfile` syntax is correct
- Ensure `requirements.txt` has all dependencies
- Check that all files are committed to Git

#### 2. **App Starts But Shows Errors**

**Symptoms**: App loads but shows BigQuery connection errors

**Solutions**:
- Verify environment variables are set correctly
- Check `GOOGLE_BIGQUERY_CREDENTIALS` is valid JSON (single-line)
- Verify `GOOGLE_LLM_API_KEY` is correct
- Check service logs: AWS Console → Your service → "Logs" tab

#### 3. **App Is Slow**

**Symptoms**: Long loading times

**Solutions**:
- Increase CPU/Memory in service configuration
- Check if BigQuery queries are taking too long
- Review service metrics in AWS Console

#### 4. **Can't Access App**

**Symptoms**: URL returns error or times out

**Solutions**:
- Verify service status is "Running" (not "Creating" or "Failed")
- Check that ingress is set to "Public"
- Wait a few minutes after deployment (DNS propagation)

### Viewing Logs

1. Go to AWS App Runner console
2. Click your service name
3. Click "Logs" tab
4. You'll see real-time logs from your application
5. Use these to debug issues

### Checking Service Health

1. In your service, go to "Metrics" tab
2. Check:
   - **CPU Utilization**: Should be < 80%
   - **Memory Utilization**: Should be < 80%
   - **Request Count**: Number of requests
   - **Response Time**: Should be < 2 seconds

---

## Understanding Costs

### AWS App Runner Pricing (as of 2024)

- **Compute**: ~$0.007 per vCPU-hour
- **Memory**: ~$0.0008 per GB-hour
- **Example**: 0.25 vCPU + 0.5 GB running 24/7 = ~$5-10/month

### Free Tier

- **750 hours/month** of App Runner for 12 months
- Enough to run 1 small instance continuously

### Cost Optimization Tips

1. **Set min instances to 0** (if you don't need 24/7 availability)
2. **Use smaller CPU/Memory** if app is slow but not overloaded
3. **Monitor usage** in AWS Cost Explorer

---

## Next Steps

After successful deployment:

1. **Test your app** thoroughly with the public URL
2. **Set up monitoring** (CloudWatch alarms for errors)
3. **Configure custom domain** (optional)
4. **Set up CI/CD** (automatic deployments on Git push)
5. **Review security** (ensure credentials are secure)

---

## Quick Reference Commands

### Windows PowerShell Commands

```powershell
# Navigate to project
cd C:\Users\Longin\Desktop\Projects\auto_sql

# Check Git status
git status

# Add and commit changes
git add .
git commit -m "Your commit message"
git push

# View AWS App Runner services (if AWS CLI installed)
aws apprunner list-services
```

---

## Summary

**Deployment Flow**:
1. ✅ Code in GitHub
2. ✅ Dockerfile created
3. ✅ AWS Account ready
4. ✅ Create App Runner service
5. ✅ Connect to GitHub
6. ✅ Configure environment variables
7. ✅ Deploy
8. ✅ Access via public URL

**Key Concepts**:
- **Container**: Isolated environment with your app
- **Dockerfile**: Instructions for building the container
- **Environment Variables**: Secure way to store credentials
- **App Runner**: AWS service that runs your container automatically

Your app is now live in the cloud! 🚀


