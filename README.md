# Owolot landing page

The public landing page for Owolot, a local-first personal finance app for iOS
and Android. The site uses FastHTML with Starlette/ASGI, Uvicorn, server-rendered
HTML, and custom CSS. Brand artwork is served from `assets/`.

## Local development

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --extra test
uv run uvicorn main:app --reload
```

Open <http://127.0.0.1:8000>. Run the tests with:

```sh
uv run pytest
```

## Configuration and environment variables

| Variable | Required | Secret | Purpose |
| --- | --- | --- | --- |
| `PORT` | Optional | No | HTTP listen port for local or container runs (default `8000`). |
| `DATABASE_PATH` | Optional | No | Local SQLite file path used when neither MongoDB nor Supabase is configured (default `data/beta_requests.sqlite3`). |
| `BETA_ADMIN_USERNAME` | Required for `/beta` & `/admin/beta` | Yes | HTTP Basic Auth username for `/admin/beta`. Beta submissions are disabled until both admin credentials are set. |
| `BETA_ADMIN_PASSWORD` | Required for `/beta` & `/admin/beta` | Yes | HTTP Basic Auth password for `/admin/beta`. |
| `MONGODB_URI` | Optional (Recommended on Vercel) | Yes | MongoDB Atlas connection string (`mongodb+srv://...`) used to store and read `beta_requests`. |
| `MONGODB_DATABASE` | Optional | No | MongoDB database name within your cluster (default `owolot`). Set a distinct name per app when sharing one Atlas cluster across multiple apps. |
| `SUPABASE_URL` | Optional | No | Supabase project URL (`https://<project-ref>.supabase.co`). Must be set together with `SUPABASE_SERVICE_ROLE_KEY` if using Supabase instead of MongoDB. |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | Yes | Server-side Supabase service role key used to insert and list rows in `public.beta_requests`. |

## Vercel deployment (with MongoDB Atlas Free Tier)

Because Vercel runs Python in ephemeral serverless functions without a persistent local disk, configure MongoDB Atlas (or Supabase) for beta request storage when deploying to Vercel:

1. **Create a free MongoDB Atlas cluster (`M0`):**
   - In [MongoDB Atlas](https://www.mongodb.com/atlas), create a free `M0` cluster.
   - Under **Security → Database Access**, create a database user and password.
   - Under **Security → Network Access**, add IP address `0.0.0.0/0` (*Allow Access from Anywhere*) so Vercel's serverless functions can reach the cluster.
   - Click **Connect → Drivers and Client Libraries**, choose **Python**, and copy your connection string (`mongodb+srv://<username>:<password>@...`).

2. **Import the repository in Vercel:**
   - Open [vercel.com/new](https://vercel.com/new) and import this GitHub repository (`owolotCustomer`).
   - Vercel automatically reads `vercel.json` and builds `main.py` with `@vercel/python`.

3. **Set Environment Variables in Vercel:**
   In Vercel **Project Settings → Environment Variables**, add:
   - `BETA_ADMIN_USERNAME` = `<your-admin-username>`
   - `BETA_ADMIN_PASSWORD` = `<your-strong-admin-password>`
   - `MONGODB_URI` = `mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority`
   - `MONGODB_DATABASE` = `owolot_customer` *(optional, defaults to `owolot`)*

4. **Deploy:**
   Click **Deploy** (or push to `main`). MongoDB automatically creates the `owolot_customer` database and `beta_requests` collection on the first submission. Visit your `https://<project>.vercel.app` URL and `/admin/beta` to verify.

## AWS Free Tier deployment

The GitHub Actions workflow (`.github/workflows/deploy-aws.yml`) builds and
publishes the Docker image to Amazon ECR, then deploys `infra/aws/stack.yaml`
using AWS Free Tier eligible resources:
- **EC2 (`t3.micro` or `t2.micro`):** 1 instance with 1 public IPv4 address (750 hours/month in the 12-month Free Tier).
- **Encrypted EBS (`gp3`):** 16 GB root volume + 4 GB retained data volume (`20 GB` total, within the 30 GB EBS Free Tier limit) storing `/data/beta_requests.sqlite3`.
- **CloudFront HTTPS distribution:** Redirects HTTP to HTTPS (Always Free tier includes 1 TB data transfer out/month and 10M HTTP/HTTPS requests/month).
- **SSM Parameter Store Standard (`SecureString`):** Stores the auto-generated admin password at `/owolot-customer/beta-admin-password` ($0/month Always Free, avoiding Secrets Manager charges).
- **CloudWatch Logs:** 14-day retention log group (`/owolot-customer/app`, within the 5 GB Always Free limit).

Requests reach the EC2 instance only from CloudFront's managed origin prefix
list on port `8000`; HTTP viewers are redirected to HTTPS.

### One-time GitHub and AWS setup

1. In AWS IAM, add the GitHub Actions OIDC identity provider:
   `https://token.actions.githubusercontent.com` with audience
   `sts.amazonaws.com` (skip this if it already exists).
2. Create an IAM role trusted for web identity from that provider. Restrict its
   trust policy to the repository and deployment branch:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {
         "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
       },
       "Action": "sts:AssumeRoleWithWebIdentity",
       "Condition": {
         "StringEquals": {
           "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
           "token.actions.githubusercontent.com:sub": "repo:dmarcllanes/owolotCustomer:ref:refs/heads/main"
         }
       }
     }]
   }
   ```

3. Give this role only the deployment permissions required by the workflow and
   stack: create/push to the `owolot-customer` ECR repository; deploy and read
   the `owolot-customer` CloudFormation stack; inspect EC2 managed prefix
   lists; create/manage the VPC, security group, EC2 instance, EBS volumes,
   CloudFront distribution, CloudWatch log group, SSM parameter
   `/owolot-customer/beta-admin-password`, SSM Run Command execution, and IAM
   instance profile declared in the template; and pass the stack's EC2 role to
   `ec2.amazonaws.com`.
4. In GitHub repository **Settings → Secrets and variables → Actions**, add:

   | Name | Type | Value |
   | --- | --- | --- |
   | `AWS_REGION` | Repository variable | The AWS region to deploy into, for example `us-east-1`. |
   | `AWS_ROLE_ARN` | Repository secret | The ARN of the GitHub OIDC deployment role. |

5. Push to `main` or run **Actions → Deploy to AWS → Run workflow**. The first
   deployment creates the ECR repository, generates the SSM admin password, and
   provisions all application resources. Subsequent deployments update the
   running Docker container via AWS Systems Manager (SSM) Run Command.

### Admin access and persistent data

- The admin username is `owolot-admin` and the password is stored in AWS Systems
  Manager Parameter Store (`/owolot-customer/beta-admin-password`). Retrieve it
  from a trusted local terminal:

  ```sh
  aws ssm get-parameter \
    --name /owolot-customer/beta-admin-password \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text
  ```

  Keep the result private. Use `owolot-admin` and this password at `/admin/beta`.
- The stack mounts a dedicated 4 GB encrypted EBS volume at `/data` and sets
  `DATABASE_PATH=/data/beta_requests.sqlite3`. CloudFormation retains this EBS
  volume if the stack is deleted.
- The site and admin page are served through CloudFront. HTTP requests redirect
  to HTTPS, and the EC2 security group accepts origin traffic only from
  CloudFront's AWS-managed prefix list.
- Rotate the dashboard password in SSM Parameter Store when needed, then re-run
  the deployment workflow so the container restarts with the rotated secret.
- Decide and document a retention/deletion schedule for beta request emails
  before launch. The admin page is read-only and does not delete requests;
  until a deletion workflow is added, an operator must manage retention in the
  SQLite database.

## Content and launch checklist

- The page describes product behavior based on the current product brief; update
  `main.py` when verified app behavior changes.
- `/beta` accepts an email address and iOS/Android selection after explicit
  consent. Requests are stored in SQLite; `/admin/beta` lists the latest 500
  requests for a manually authenticated admin. It does not send email or grant
  store access automatically. Both admin credential variables must be set
  before a beta request can be accepted; otherwise the form shows that requests
  are unavailable.
- Decide and document a retention/deletion schedule for beta request emails
  before launch. The admin page is read-only and does not delete requests;
  until a deletion workflow is added, an operator must manage retention in the
  SQLite database directly.
- Configure and verify the iOS TestFlight and Android Google Play testing
  tracks before sending installation instructions. No invite links are
  published on the site.
- To create an iOS invite: in App Store Connect, open the app's TestFlight
  page, add a tester group and build for external testing, then enable a public
  link for that group after completing Apple's required review steps. You can
  also invite testers by email. Send the resulting invite to approved
  applicants yourself.
- To create an Android invite: in Google Play Console, configure a closed or
  internal testing track, add the tester email/group or enable its opt-in
  link, and publish the test release. Send approved applicants the appropriate
  opt-in and Play installation instructions yourself.
- No production domain is confirmed, so the page intentionally has no canonical
  URL.
- `/privacy` contains the privacy policy for store submission. Before publishing
  the site or submitting its URL in App Store Connect or Google Play Console,
  verify the policy against the exact app build and current provider terms,
  confirm the listed privacy contact, and deploy to a public HTTPS domain.
- `PRODUCT_NAME` in `main.py` is the single source for the displayed product
  name.
