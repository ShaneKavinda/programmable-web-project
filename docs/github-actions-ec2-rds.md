# GitHub Actions + AWS EC2 + RDS Deployment Guide

This repo now includes:

- `/.github/workflows/ci.yml` to run `pytest` on pushes and pull requests
- `/.github/workflows/deploy.yml` to deploy `aws-deploy-shane` to an EC2 instance over SSH
- `/scripts/deploy_ec2.sh` to update the server and restart the containers
- `/ticket_management_system/docker-compose.prod.yml` for EC2 deployments that use an external PostgreSQL database such as Amazon RDS

## 1. Architecture

Use this layout:

- GitHub Actions for CI and deployment orchestration
- One EC2 instance for Docker, Nginx, and the Flask API
- One RDS PostgreSQL instance for the database

The app container now reads the database host from `DATABASE_URL`, so it can connect to either the local Docker Postgres container used in development or an external RDS endpoint in production.

## 1.1 Branch Strategy

This setup assumes you are validating AWS deployment work from the `aws-deploy-shane` branch so the main branch stays untouched while you test infrastructure changes.

- CI runs on pushes to `aws-deploy-shane`
- CD deploys only from `aws-deploy-shane`
- Manual deployments from GitHub Actions also default to `aws-deploy-shane`
- No workflow in this setup pushes commits or merges changes into `main`

When you are ready to promote the pipeline to `main`, update the branch filters in `/.github/workflows/ci.yml` and `/.github/workflows/deploy.yml`.

## 2. Free Tier Note

AWS changed its Free Tier on July 15, 2025. If your AWS account was created on or after that date, AWS uses a credit-based free plan for up to 6 months. Older accounts can still have the classic instance-hour style benefits for up to 12 months. Check your account's actual Free Tier eligibility before creating resources.

## 3. Create The RDS PostgreSQL Instance

Recommended baseline:

- Engine: PostgreSQL
- Deployment: Single-AZ
- Instance class: a free-tier-eligible micro option available to your account
- Storage: stay within the Free Tier allowance for your account
- Public access: `No`
- Automatic minor version upgrade: `Yes`
- Backup retention: keep it small if you are cost-sensitive

Networking:

- Put EC2 and RDS in the same VPC
- Create an RDS security group that allows port `5432` only from the EC2 security group
- Do not open PostgreSQL to the public internet

Create a database, user, and password, then build a URL like this:

```dotenv
DATABASE_URL=postgresql://app_user:app_password@your-rds-endpoint.region.rds.amazonaws.com:5432/flask_db?sslmode=require
```

If your password contains special characters, URL-encode it before placing it in `DATABASE_URL`.

## 4. Launch The EC2 Instance

Use a Linux AMI such as Amazon Linux 2023 and attach a security group with:

- Inbound `22` from your IP only
- Inbound `80` from `0.0.0.0/0`
- Inbound `443` from `0.0.0.0/0` if you add TLS later

One-time setup on the instance:

```bash
sudo dnf update -y
sudo dnf install -y git docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
newgrp docker

mkdir -p ~/apps
cd ~/apps
git clone https://github.com/<your-org-or-user>/<your-repo>.git programmable-web-project
cd ~/apps/programmable-web-project
git checkout aws-deploy-shane
chmod +x scripts/deploy_ec2.sh
```

Create the production environment file expected by `ticket_management_system/docker-compose.prod.yml`:

```bash
cp ticket_management_system/.env.example ticket_management_system/.env
```

Then edit `ticket_management_system/.env` so it contains real production values:

```dotenv
DATABASE_URL=postgresql://app_user:app_password@your-rds-endpoint.region.rds.amazonaws.com:5432/flask_db?sslmode=require
JWT_SECRET_KEY=replace-with-a-long-random-secret
WEB_CONCURRENCY=2
GUNICORN_TIMEOUT=30
DB_WAIT_TIMEOUT=60
```

First manual deployment:

```bash
docker compose -f ticket_management_system/docker-compose.prod.yml up -d --build
curl http://localhost/healthz
curl http://localhost/
```

## 5. GitHub Secrets

Add these GitHub Actions secrets at the repository level, or in a `production` environment if your GitHub plan supports environment secrets for your repo type:

- `EC2_HOST`: public DNS name or public IP of the EC2 instance
- `EC2_USER`: typically `ec2-user` for Amazon Linux
- `EC2_SSH_PRIVATE_KEY`: the private key that matches the EC2 instance key pair
- `EC2_KNOWN_HOSTS`: output of `ssh-keyscan -H <your-ec2-host>`
- `EC2_APP_DIR`: absolute path to the repo on the server, for example `/home/ec2-user/apps/programmable-web-project`
- `EC2_SSH_PORT`: optional, defaults to `22`

Example for generating `EC2_KNOWN_HOSTS` locally:

```bash
ssh-keyscan -H your-ec2-host.amazonaws.com
```

## 6. What The Pipeline Does

`CI` workflow:

- Checks out the repo
- Installs Python 3.11
- Installs dependencies from `ticket_management_system/requirements.txt`
- Runs `pytest -q`

`Deploy To EC2` workflow:

- Runs on pushes to `aws-deploy-shane`
- Opens an SSH session to EC2
- Runs `scripts/deploy_ec2.sh`
- Pulls the latest code
- Rebuilds the API image
- Starts the production Compose stack
- Verifies the Nginx health endpoint

## 7. Production Compose File

Use this command on the EC2 host:

```bash
docker compose -f ticket_management_system/docker-compose.prod.yml up -d --build
```

This production file intentionally omits the local `postgres` container because PostgreSQL lives in RDS.

## 8. Optional Hardening

Once the basic flow works, I recommend adding:

- HTTPS with Nginx plus Certbot or an AWS load balancer
- A domain name in Route 53 or your DNS provider
- EC2 instance backups or an AMI snapshot plan
- CloudWatch alarms for CPU, disk, and RDS storage
- A non-root deployment user if you do not want to use the default EC2 account

## 9. Troubleshooting

If deploys fail:

- Check the GitHub Actions log first
- SSH into EC2 and run `docker compose -f ticket_management_system/docker-compose.prod.yml logs -f`
- Confirm `ticket_management_system/.env` exists on the server
- Confirm `DATABASE_URL` points to the RDS endpoint, not `localhost`
- Confirm the RDS security group allows `5432` from the EC2 security group
- Confirm the EC2 instance and RDS instance are in the same VPC or otherwise routable
