# Using infrastructure as code in `Google Cloud Platform`

Here, I will explain how I have used `Terraform`, an infrastructure as code (`IaC`) tool, to safely and predictably provision and manage infrastructure in `Google Cloud Platform` (`GCP`).

Note that `Terraform` also supports other cloud platforms, such as `Amazon Web Services` (`AWS`) and Microsoft `Azure`.

## Table of contents
1. [:wrench: Setting up the `Google Cloud CLI`](#gcloud-init)
2. [:name_badge: GCP credentials & authentication](#gcp-auth)
    1. [:ticket: Creating a new GCP's `service account` associated with our currently activated `GCP project`](#service-account)
    2. [:black_joker: Using `Service account` impersonation](#sa-impersonation)
    3. [:paperclip: Using service account attachment to the `VM template`](#sa-attachment)
    4. [:closed_lock_with_key: Using `SSH` keys with `GCP VM`s](#sa-keys)
3. [:clipboard: Creating a `VM instance template`](#vm-instance-template)
4. [:rocket: Deploying `GCP VM`s instances using `Terraform`](#tf-deploy)

<div id="gcloud-init"></div>

## :wrench: Setting up the `Google Cloud CLI`

I started by installing the `Google Cloud CLI` (`gcloud CLI`) in my host machine:

```
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-cli
```

See the [GCP Official documentation](https://cloud.google.com/sdk/docs/install) for details about how to install the `gcloud CLI` in other platforms (e.g., `RedHat`, `macOS`, `Windows`) [^1].

Next, I set up `gcloud CLI` [^3][^4]:

```
gcloud init --no-launch-browser
```

and enable the `Compute Engine API`:

```
gcloud services enable compute.googleapis.com
```

Now, I was ready to create a new `GCP project` [^2] called `fmerinocasallo-nyc-taxi`:

```
gcloud projects create fmerinocasallo-nyc-taxi
```

Replace `fmerinocasallo-nyc-taxi` with your preferred name for the new `GCP project` to be created.

Next, I set the newly created `GCP project` as the current activated project:
```
gcloud config set project fmerinocasallo-nyc-taxi
```

Again, replace `fmerinocasallo-nyc-taxi` with the `GCP project` name of your choosing.

Finally, I set a specific `GCP region` and `GCP zone` for my newly created `GCP project`. You may be interested in picking one of the closest locations to your host machine to opt for fast communications to `GCP`. Note that some `GCP zone`s are identified as Low CO<sub>2</sub> (e.g., Finland, Montréal, Sāo Paulo) [^5].

```
gcloud compute project-info add-metadata \\
   --metadata google-compute-default-region=europe-southwest1,google-compute-default-zone=europe-southwest1-a
```

Replace `europe-southwest1` (Madrid) and `europe-southwest1-a` with your preferred `GCP region` and `GCP zone`.

To get a list of the available `GCP region`s and `GCP zone`s, run:

```
gcloud compute regions list
gcloud compute zones list
```

<div id="gcp-auth"></div>

## :name_badge: GCP credentials & authentication

Making requests against the `GCP API` requires you to prove your identity by authenticating using valid `GCP` credentials. The preferred method of provisioning resources with `Terraform` on your workstation is to use the `Google Cloud SDK`.

When you access `Google Cloud services` by using the `gcloud CLI`, `Cloud Client Libraries`, tools that support `Application Default Credentials (ADC)` (e.g., `Terraform`), or `REST` requests, use the following diagram to help you choose an authentication method [^6]:

![Decision tree for choosing authentication method based on use case](https://cloud.google.com/static/docs/authentication/images/authn-tree.svg)

 This diagram guides you through the following questions:

1. Are you running code in a single-user development environment, such as your own workstation, `Cloud Shell`, or a virtual desktop interface?
    a. If yes, proceed to question 4.
    b. If no, proceed to question 2.

2. Are you running code in `Google Cloud`?
    a. If yes, proceed to question 3.
    b. If no, proceed to question 5.

3. Are you running containers in `Google Kubernetes Engine` or `GKE Enterprise`?
    a. If yes, use workload identity federation for `GKE` to attach `service account`s (`SA`s) to `Kubernetes pods`.
    b. If no, attach a `SA` to the resource.

4. Does your use case require a `SA`?
For example, you want to configure authentication and authorization consistently for your application across all environments.
    a. If no, authenticate with user credentials.
    b. If yes, impersonate a `SA` with user credentials.

5. Does your workload authenticate with an external identity provider that supports workload identity federation?
    a. If yes, configure workload identity federation to let applications running on-premises or on other cloud providers use a `SA`.
    b. If no, create a `SA` key.


See [Authentication methods at Google](https://cloud.google.com/docs/authentication) for more details about authentication methods and concepts, and where to get help with implementing or troubleshooting authentication.

<div id="service-account"></div>

### :ticket: Creating a new GCP's `service account` associated with our currently activated `GCP project`

`Service account`s are used by applications or compute workloads, rather than a person [^7], and are managed by `Identity and Access Management` (`IAM`).

The authorization provided to applications hosted on a `Compute Engine instance` is limited by two separate configurations:
1. The roles granted to the attached `SA`.
2. The access scopes that you set on the `Compute Engine instance`.

Both of these configurations must allow access for the application running on the instance being able to access a resource. `Service account`s enable applications hosted on a `Compute Engine instance` to use the `SA` credentials to authenticate to the `Cloud Storage API` without embedding any secret keys or user credentials in your instance, image, or app code.

The `SA`s documentation explains that access scopes are the legacy method of specifying permissions for your instance. To follow best practices **you should create a dedicated `SA` with the minimum permissions the `virtual machine` (`VM`) requires [^8].** To use a dedicated `SA` the `scope` field should be configured as a list containing the `cloud-platform` scope.

See [Authenticate workloads using service accounts best practices](https://cloud.google.com/compute/docs/access/create-enable-service-accounts-for-instances#best_practices) and [Best practices for using service accounts](https://cloud.google.com/iam/docs/best-practices-service-accounts#single-purpose).

Alternatively, we could use any of the following `environment variable`s ordered by precedence:

1. `GOOGLE_CREDENTIALS`
2. `GOOGLE_CLOUD_KEYFILE_JSON`
3. `GCLOUD_KEYFILE_JSON`

Using `Terraform`-specific `SA`s to authenticate with `GCP` is the recommended practice when using `Terraform`. If no `Terraform`-specific credentials are specified, the provider will fall back to using `Google Application Default Credentials` (`ADC`). To use them, you can enter the path of your `SA` key file in the `GOOGLE_APPLICATION_CREDENTIALS` `environment variable`, or configure authentication through one of the following:

1. If you are running `Terraform` from a `GCE instance`, default credentials are automatically available. See [Creating and Enabling Service Accounts for Instances](https://cloud.google.com/compute/docs/authentication) for more details.
2. On your workstation, you can make your Google identity available by running:

```
gcloud auth application-default login --no-launch-browser
```

I created a new `SA` using `gcloud CLI` [^9]:
```
gcloud iam service-accounts create vm-terraform
gcloud projects add-iam-policy-binding fmerinocasallo-nyc-taxi --member="serviceAccount:vm-terraform@fmerinocasallo-nyc-taxi.iam.gserviceaccount.com" --role=roles/compute.admin
gcloud projects add-iam-policy-binding fmerinocasallo-nyc-taxi --member="serviceAccount:vm-terraform@fmerinocasallo-nyc-taxi.iam.gserviceaccount.com" --role=roles/iam.serviceAccountUser
```

Replace `vm-terraform` with your preferred name (you may want to take into account [GCP's naming and documentation convention](https://cloud.google.com/iam/docs/best-practices-service-accounts#naming-convention)), `fmerinocasallo-nyc-taxi` with your `GCP project` name, and `vm-terraform@fmerinocasallo-nyc-taxi.iam.gserviceaccount.com` accordingly.

To list all `SA`s in the activated `GCP project`, run:

```
gcloud iam service-accounts list
```

Write down the email address of the newly created `SA`, you will need that email later on. It should look something like this: `<account-name>@<project-name>.iam.gserviceaccount.com`.

See [IAM basic and predefined roles reference](https://cloud.google.com/iam/docs/understanding-roles?authuser=2#compute-engine-roles) for a list of all basic and predefined roles for `IAM`. I opted for assigning my new `SA` the following roles:
1. `Compute Admin`: Full control of all `Compute Engine` resources.
3. `Service Account User`: Required if the user will be running operations (e.g., managing `VM instances`) as a `SA`.

Note that currently **the only supported `SA` credentials are those downloaded from `Cloud Console` or generated by `gcloud`.**

<div id="sa-impersonation"></div>

### :black_joker: Using `Service account` impersonation

I was running my code in a single-user development environment (i.e., my own workstation). I also wanted to apply the [least priviledge principle](https://en.wikipedia.org/wiki/Principle_of_least_privilege) while using `Terraform` to automate the infrastructure deployment in `GCP`. Therefore, I followed `GCP` recommendation and opted for using `SA` impersonation.

By using `SA` impersonation, I took advantadge of the least priviledge principle, which requires every module (e.g., process, user, program) to be able to access **only** the information and resources that are necessary for its legitimate purpose. As a result, instead of using my main `Principal`  (my personal user account `fmerinocasallo@gmail.com`, which has the `Owner` role), I would use a much more limited user (the newly created `SA` with just `Compute Admin` and `Service Account User` roles) when managing `VM instance`s.

To allow my main `Principal` (my personal user account: `fmerinocasallo@gmail.com`) to impersonate the newly created and least priviledged `SA` (`vm-terraform`), I assigned it the `roles/iam.serviceAccountTokenCreator` role:

```
gcloud iam service-accounts add-iam-policy-binding vm-terraform@fmerinocasallo-nyc-taxi.iam.gserviceaccount.com \
 --member="user:fmerinocasallo@gmail.com"
 --role="roles/iam.serviceAccountTokenCreator"
```

Note that it may be more appropriate to assign this role (`roles/iam.serviceAccountTokenCreator`) to a group, instead of directly to a given user.

I needed to define a new `provider`:

#### :page_facing_up: FILE `./providers.tf`:
```
provider "google" {
  alias = "vm-tf-impersonation"
  scopes = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
  ]
}
```

which would run in the context of my main `Principal` (my personal user account: `fmerinocasallo@gmail.com`), as there are no other credentials or access tokens configured. Replace `vm-tf-impersonation` with your preferred name.

I would also need a short-lived access token to authenticate as the target `SA`. To achieve this, I created a new `data` block:

#### :page_facing_up: FILE `./data.tf`:
```
#receive short-lived access token
data "google_service_account_access_token" "vm_tf_impersonation" {
  provider               = google.vm-tf-impersonation
  target_service_account = var.service_account_vm_tf_email
  scopes                 = ["cloud-platform", "userinfo-email"]
  lifetime               = "3600s"
}
```

The `lifetime` parameter limits the period of validity, one hour should be enough but you can play a little bit and use an alternative value if needed. Do not forget to update the `provider` section (`google.vm-tf-impersonation`) of this `data` block based on the previously defined `provider` block.

Note that I used a `Terraform variable` (`var.service_account_vm_tf_email`) in the `target_service_account` section, which I defined as follows:

#### :page_facing_up: FILE `./variables.tf`:

```
variable "service_account_vm_tf_email" {
  type        = string
  description = "Email adress of the service account used to manage VM instances with Terraform"
}
```

and stored its value, the corresponding email address associated with the newly created `SA`, in the `terraform.tfvars`:

#### :page_facing_up: FILE `./terraform.tfvars`:

```
service_account_vm_tf_email = "vm-terraform@fmerinocasallo-nyc-taxi.iam.gserviceaccount.com"
```

Finally, I defined a second `google` provider that would use the newly defined `data` token to create resources on behalf of the `Terraform` `SA`. With no `alias`, this will be the default `provider`:

#### :page_facing_up: FILE `./providers.tf`:
```
[...]

# default provider to use the the token
provider "google" {
  project         = var.project_id
  access_token    = data.google_service_account_access_token.vm_tf_impersonation.access_token
  request_timeout = "60s"
}
```

<div id="sa-attachment"></div>

### :paperclip: Using service account attachment to the `VM template`

If I were to run my code in `Google Cloud` but not to run containers in `Google Kubernetes Engine` or `GKE Enterprise`, I should attach a `SA` to the resource. In this case, I would need to add a `service_account` block to my definition of a `VM instance template` (`google_compute_instance_template`):

#### :page_facing_up: FILE `./resources.tf`:

```
resource "google_compute_instance_template" "co_2vc_8gb" {
  name                 = "co-2vc-8gb"
  instance_description = "GCP Cost Optimized 2 vCPUs & 8 GB RAM"
  machine_type         = "e2-standard-2"

  [...]

  # To avoid embedding secret keys or user credentials in the instances, Google recommends that you use custom service accounts with the following access scopes.
  service_account {
    email   = service_account_vm_tf_email
    scopes  = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
```

I should have previously created the `vm-terraform` `SA` used in this `service_account` block. I should also include a list of service scopes. Both `OAuth2` URLs and `gcloud` short names are supported. To allow full access to all `Cloud APIs`, use the `cloud-platform` (i.e., `https://www.googleapis.com/auth/cloud-platform`) scope. See a complete list of scopes [here](https://cloud.google.com/sdk/gcloud/reference/alpha/compute/instances/set-scopes#--scopes).

Note that I would need to specify the email address associated with the newly created `SA` in the `email` section included inside the `service_account` block. I could define a new variable called `service_account_vm_tf_email` in the `variables.tf` file as previously shown.

<div id="sa-keys"></div>

### :closed_lock_with_key: Using `SSH` keys with `GCP VM`s

There could be other scenarios were we may need or want to use `SA` keys. For example, we may want to log in to one of these `VM instance`s using:

```
gcloud compute ssh tf-instance --impersonate-service-account=vm-terraform@fmerinocasallo-nyc-taxi.iam.gserviceaccount.com
```

Do not forget to replace `vm-terraform@fmerinocasallo-nyc-taxi.iam.gserviceaccount.com` accordingly, as follows: `<Service Account name>@<Project ID>.iam.gserviceaccount.com`.

Note that if there are no `SA` keys (i.e., private/public `SSH` key files for `gcloud`) already included in the metadata of the `VM instance` or `GCP project`, `gcloud compute ssh` would start by executing `SSH keygen` to generate a new key. The new identification would then be saved in `~/.ssh/google_compute_engine` and the new public key in `~/.ssh/google_compute_engine.pub`. Finally, it would update the `GCP project` `SSH` `metadata` accordingly, and propagate the new `SSH` key.

We could also log in to one of these `VM instance`s using a different `SSH` client:

```
ssh -p 22 fmerinocasallo@34.0.221.100
```

Replace `fmerinocasallo` with your personal user account and `34.0.221.100` with the External IP address assigned to the new `VM instance` deployed by `Terraform` in `GCE`.

In this case, we would need to start by creating a new `SSH` key for `GCP` [^10] using `SSH keygen`:

```
ssh-keygen -t ed25519 -f .ssh/id_ed25519_gcp -C "fmerinocasallo"
```

Note that I have replaced the default `rsa` cryptographic algorithm by the generally considered more secured and efficient `ed25519` one.

Surprisingly, we would have to adapt the default format of the newly created `SSH` public key to the `GCP CLI`'s requirements by adding the desired username (`fmerinocasallo` in my case, replace accordingly) at the beginning of the line:

#### :page_facing_up: FILE `~/.ssh/id_ed25519_gcp.pub`:
```
fmerinocasallo:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBJQRXzWgdYNbY5ZMF+KJQhRGY2ovNJpPcPFX7h7HZao fmerinocasallo
```

Otherwise, we would have seen the following WARNING message when trying to add the newly created `SSH` public key to the currently activated `GCP project`:

```
WARNING: The following key(s) are missing the <username> at the front
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBJQRXzWgdYNbY5ZMF+KJQhRGY2ovNJpPcPFX7h7HZao fmerinocasallo
```

Next, we could add the newly created SSH public key to the currently activated `GCP project` (`fmerinocasallo-nyc-taxi` in this case) [^11].

```
gcloud compute project-info add-metadata --metadata-from-file=ssh-keys=~/.ssh/id_ed25519_gcp.pub
```

Replace `~/.ssh/id_ed25519_gcp.pub` with the path of your desired `SSH` public key.

An interesting and potentially more secured alternative would require adding this `SSH` public key only to a `VM instance template`:

#### :page_facing_up: FILE `./resources.tf`:
```
  resource "google_compute_instance_template" "co_2vc_8gb" {

  [...]

  metadata = {
    "ssh-keys" = <<EOT
      fmerinocasallo:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBJQRXzWgdYNbY5ZMF+KJQhRGY2ovNJpPcPFX7h7HZao fmerinocasallo
     EOT
  }
```
or a particular `VM instance`:

#### :page_facing_up: FILE `./resources.tf`:
```
[...]

resource "google_compute_instance_from_template" "tf_instance" {
  name                      = "tf-instance"
  zone                      = var.zone
  source_instance_template  = google_compute_instance_template.co_2vc_8gb.self_link_unique

  metadata = {
    "ssh-keys" = <<EOT
      fmerinocasallo:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBJQRXzWgdYNbY5ZMF+KJQhRGY2ovNJpPcPFX7h7HZao fmerinocasallo
     EOT
  }
}
```

<div id="vm-instance-template"></div>

## :clipboard: Create a `VM instance template`

I opted to use `Terraform` to create a `GCP` instance template [^12][^13] as follows:

#### :page_facing_up: FILE `./resources.tf`:
```
resource "google_compute_instance_template" "co_2vc_8gb" {
  name                  = "co-2vc-8gb"
  instance_description  = "GCP Cost Optimized 2 vCPUs & 8 GB RAM"
  machine_type          = "e2-standard-2"

  disk {
    source_image  = "debian-cloud/debian-12"
    auto_delete   = true
    boot          = true
    disk_size_gb  = 30
  }

  network_interface {
    network = "default"

    # default access config, defining external IP configuration
    access_config {
      network_tier = "STANDARD"
    }
  }
}

[...]
```

See `GCP`'s [Machine families resource and comparison guide](https://cloud.google.com/compute/docs/machine-resource) for details about the different `machine-type`s available in `GCP` [^14].

See `GCP`'s [Network Service Tiers overview](https://cloud.google.com/network-tiers/docs/overview) for more details about the different `Network Service Tiers` offered [^15].

Then, I was able to create a new `GCP` `VM instance` from the instance template we have just defined [^16][^17]:

#### :page_facing_up: FILE `./resources.tf`:
```
[...]

resource "google_compute_instance_from_template" "tf-instance" {
  name                      = "tf-instance"
  zone                      = var.zone
  source_instance_template  = google_compute_instance_template.co_2vc_8gb.self_link_unique
}
```

<div id="tf-deploy"></div>

## :rocket: Deploying `GCP VM`s instances using `Terraform`

To deploy with `Terraform` the defined infrastructure, I run the following commands:

```
terraform fmt
terraform validate
terraform plan -out plan.tf
terraform apply plan.tf
```

Then, to connect to the `GCP instance` I had just created, I could run if I opt to use `SA` keys:

```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519_gcp
ssh -p 22 fmerinocasallo@34.0.222.24
```

Replace `34.0.222.24` with the corresponding External IP address of your `VM instance`.

Note that to establish a `SSH` connection with the deployed `VM instance`, I had previously generated a pair of `SSH` keys (public and private) using `SSH keygen` as previously shown.

Lastly, to destroy the defined infrastructure, simply run:

```
terraform destroy
```

[^1]: Google Cloud Official Documentation: Install the gcloud CLI (accessed on 17/09/2024): https://cloud.google.com/sdk/docs/install
[^2]: Google Cloud Official Documentation: Creating and managing projects (accessed on 17/09/2024): https://cloud.google.com/resource-manager/docs/creating-managing-projects
[^3]: Google Cloud Official Documentation: Initializing the gcloud CLI (accessed on 17/09/2024): https://cloud.google.com/sdk/docs/initializing
[^4]: Google Cloud Official Documentation:  Quickstart: Create a VM instance using Terraform (accessed on 17/09/2024): https://cloud.google.com/docs/terraform/create-vm-instance
[^5]: Google Cloud Official Documentation: Carbon free energy for Google Cloud regions (accessed on 17/09/2024): https://cloud.google.com/sustainability/region-carbon
[^6]: Google Cloud Official Documentation: Best practices for using service accounts > Choose when to use service accounts (accessed on 18/09/2024): https://cloud.google.com/iam/docs/best-practices-service-accounts#choose-when-to-use
[^7]: Google Cloud Official Documentation: Service accounts (accessed on 18/09/2024): https://cloud.google.com/compute/docs/access/service-accounts
[^8]: Google Cloud Official Documentation: Best practices for using service accounts (accessed on 18/07/2024): https://cloud.google.com/iam/docs/best-practices-service-accounts
[^9]: Google Cloud Official Documentation: Create a VM that uses a user-managed service account (accesed on 20/09/2024): https://cloud.google.com/compute/docs/access/create-enable-service-accounts-for-instances#createanewserviceaccount
[^10]: Google Cloud Official Documentation: Create SSH keys (accessed on 17/09/2024): https://cloud.google.com/compute/docs/connect/create-ssh-keys
[^11]: Google Cloud Official Documentation: Add SSH keys to VMs (accessed on 17/09/2024): https://cloud.google.com/compute/docs/connect/add-ssh-keys#gcloud_1
[^12]: Google Cloud Official Documentation: Create instance templates (accessed on 17/09/2024): https://cloud.google.com/compute/docs/instance-templates/create-instance-templates#terraform
[^13]: Terraform Registry: google_compute_instance_template (accessed on 18/09/2024): https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance_template
[^14]: Google Cloud Official Documentation: Machine families resource and comparison guide (accessed on 17/09/2024): https://cloud.google.com/compute/docs/machine-resource
[^15]: Google Cloud Official Documentation: Network Service Tiers overview (accessed on 17/09/2024): https://cloud.google.com/network-tiers/docs/overview
[^16]: Terraform Registry: google_compute_instance_from_template (accessed on 17/09/2024): https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance_from_template
[^17]: Google Cloud Official Documentation: Create a VM from an instance template (accessed on 17/09/2024): https://cloud.google.com/compute/docs/instances/create-vm-from-instance-template#gcloud