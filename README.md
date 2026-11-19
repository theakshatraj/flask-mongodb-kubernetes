# Flask + MongoDB on Kubernetes

A containerized Flask REST API connected to an authenticated MongoDB database, deployed on Kubernetes using Minikube. The project demonstrates persistent storage, Kubernetes service discovery, resource management, health probes, and Horizontal Pod Autoscaling (HPA).

## Overview

This project deploys a Flask application and MongoDB as separate Kubernetes workloads.

The Flask application exposes REST endpoints to insert and retrieve JSON documents. MongoDB stores the documents persistently using a PersistentVolume (PV) and PersistentVolumeClaim (PVC).

Kubernetes manages the application through Deployments, StatefulSets, Services, Secrets, and Horizontal Pod Autoscaling.

## Architecture

```text
                    Client
                      |
                      |
              Flask NodePort Service
                 Port: 30080
                      |
                      |
              Flask Deployment
                2–5 Replicas
                      |
                 Port: 5000
                      |
              Internal DNS Service
                 mongodb:27017
                      |
                      |
              MongoDB StatefulSet
                  1 Replica
                      |
               Persistent Volume
                    1 GiB
                      |
                MongoDB Storage
```

### Components

| Component | Kubernetes Resource | Purpose |
|---|---|---|
| Flask API | Deployment | Runs the application with multiple replicas |
| Flask Service | NodePort | Exposes the API outside the cluster |
| MongoDB | StatefulSet | Runs the database with stable identity |
| MongoDB Service | ClusterIP | Provides internal database connectivity |
| MongoDB Headless Service | Headless Service | Provides network identity for the StatefulSet |
| PersistentVolume | PV | Provides persistent storage |
| PersistentVolumeClaim | PVC | Requests storage for MongoDB |
| MongoDB credentials | Secret | Stores database root credentials |
| MongoDB connection URI | Secret | Supplies the connection string to Flask |
| Flask HPA | HorizontalPodAutoscaler | Scales Flask replicas based on CPU utilization |

## Technology Stack

- Python 3.10
- Flask 2.0.2
- PyMongo 3.12.0
- Gunicorn 21.2.0
- MongoDB 6
- Docker
- Kubernetes
- Minikube
- Kubernetes Metrics Server
- PowerShell

## Project Structure

```text
flask-mongodb-kubernetes/
│
├── app/
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .dockerignore
│
├── kubernetes/
│   ├── flask-deployment.yaml
│   ├── flask-hpa.yaml
│   ├── flask-service.yaml
│   ├── mongodb-pv.yaml
│   ├── mongodb-pvc.yaml
│   ├── mongodb-service.yaml
│   └── mongodb-statefulset.yaml
│
├── .gitignore
└── README.md
```

## Application API

The Flask application provides two endpoints.

### GET /

Returns a welcome message and the current server time.

```http
GET /
```

### POST /data

Inserts a JSON document into the MongoDB `flask_db.data` collection.

Example request:

```json
{
  "name": "Kubernetes Test",
  "project": "Flask MongoDB Assignment"
}
```

Response:

```json
{
  "status": "Data inserted"
}
```

HTTP status: `201 Created`

### GET /data

Retrieves all documents from the MongoDB collection.

```http
GET /data
```

The endpoint excludes MongoDB's internal `_id` field from the returned JSON documents.

## Prerequisites

Install the following tools:

- Docker Desktop
- Minikube
- kubectl
- Docker Hub account
- PowerShell

Verify installations:

```powershell
docker --version
kubectl version --client
minikube version
```

## Deployment Guide

The following instructions use Windows PowerShell.

### 1. Start Minikube

```powershell
minikube start --driver=docker
```

Enable the Metrics Server:

```powershell
minikube addons enable metrics-server
```

Verify node metrics:

```powershell
kubectl top nodes
```

### 2. Build and Push the Docker Image

Navigate to the project directory:

```powershell
cd "C:\D Drive\Coding\Placements\flask-mongodb-kubernetes"
```

Build the Flask application image:

```powershell
docker build -t theakshatraj/flask-mongodb-kubernetes:v1 ./app
```

Log in to Docker Hub:

```powershell
docker login
```

Push the image:

```powershell
docker push theakshatraj/flask-mongodb-kubernetes:v1
```

Load the image into Minikube:

```powershell
minikube image load theakshatraj/flask-mongodb-kubernetes:v1
```

### 3. Create the Kubernetes Namespace

```powershell
kubectl create namespace flask-mongodb
```

The namespace isolates the application's Kubernetes resources.

### 4. Create MongoDB Credentials

Create a Kubernetes Secret containing the MongoDB root username and password.

```powershell
$env:MONGO_ROOT_USERNAME = "mongoAdmin"
$env:MONGO_ROOT_PASSWORD = Read-Host "Enter a strong MongoDB password"

kubectl create secret generic mongodb-secret `
  --namespace flask-mongodb `
  --from-literal=username=$env:MONGO_ROOT_USERNAME `
  --from-literal=password=$env:MONGO_ROOT_PASSWORD
```

Do not commit actual credentials or generated Secret values to Git.

### 5. Configure Persistent Storage

Apply the PersistentVolume:

```powershell
kubectl apply -f kubernetes/mongodb-pv.yaml
```

Apply the PersistentVolumeClaim:

```powershell
kubectl apply -f kubernetes/mongodb-pvc.yaml
```

Verify storage binding:

```powershell
kubectl get pv
kubectl get pvc -n flask-mongodb
```

The PVC should reach the `Bound` status.

### 6. Deploy MongoDB

Create the MongoDB Services:

```powershell
kubectl apply -f kubernetes/mongodb-service.yaml
```

Deploy the MongoDB StatefulSet:

```powershell
kubectl apply -f kubernetes/mongodb-statefulset.yaml
```

Wait for MongoDB:

```powershell
kubectl rollout status statefulset/mongodb -n flask-mongodb
```

Verify:

```powershell
kubectl get pods -n flask-mongodb
```

MongoDB should be running as `mongodb-0`.

### 7. Configure the Flask Database Connection

Flask receives its MongoDB connection string through the `MONGODB_URI` environment variable, sourced from the `mongodb-app-secret` Kubernetes Secret.

The connection URI follows this format:

```text
mongodb://<encoded-username>:<encoded-password>@mongodb:27017/flask_db?authSource=admin
```

Create the application Secret using the existing MongoDB credentials:

```powershell
$usernameB64 = (kubectl get secret mongodb-secret -n flask-mongodb -o "jsonpath={.data.username}").Trim()

$passwordB64 = (kubectl get secret mongodb-secret -n flask-mongodb -o "jsonpath={.data.password}").Trim()

$username = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String($usernameB64)
)

$password = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String($passwordB64)
)

$encodedUsername = [uri]::EscapeDataString($username)
$encodedPassword = [uri]::EscapeDataString($password)

$mongoUri = "mongodb://${encodedUsername}:${encodedPassword}@mongodb:27017/flask_db?authSource=admin"

kubectl create secret generic mongodb-app-secret `
  --namespace flask-mongodb `
  --from-literal="MONGODB_URI=$mongoUri" `
  --dry-run=client -o yaml | kubectl apply -f -
```

The connection string is stored in a Kubernetes Secret rather than directly in the Deployment manifest.

### 8. Deploy Flask

Apply the Flask Deployment:

```powershell
kubectl apply -f kubernetes/flask-deployment.yaml
```

Apply the Flask Service:

```powershell
kubectl apply -f kubernetes/flask-service.yaml
```

Wait for the Deployment:

```powershell
kubectl rollout status deployment/flask-app -n flask-mongodb
```

Check the pods:

```powershell
kubectl get pods -n flask-mongodb
```

The initial desired state is two Flask replicas.

### 9. Configure Horizontal Pod Autoscaling

Apply the HPA:

```powershell
kubectl apply -f kubernetes/flask-hpa.yaml
```

Check autoscaling:

```powershell
kubectl get hpa -n flask-mongodb
```

The configuration uses:

| Setting | Value |
|---|---:|
| Minimum replicas | 2 |
| Maximum replicas | 5 |
| CPU utilization target | 70% |

### 10. Access the Application

Start the Minikube service tunnel:

```powershell
minikube service flask-service -n flask-mongodb --url
```

Keep this PowerShell window open.

Use the generated URL in another PowerShell window.

Test the root endpoint:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:<PORT>/" -Method GET
```

Replace `<PORT>` with the port generated by Minikube.

## Kubernetes DNS and Service Discovery

Kubernetes provides internal DNS resolution for Services.

The Flask application connects to MongoDB using:

```text
mongodb:27017
```

Because both workloads are deployed in the `flask-mongodb` namespace, Kubernetes resolves `mongodb` to the ClusterIP of the MongoDB Service.

The fully qualified DNS name is:

```text
mongodb.flask-mongodb.svc.cluster.local
```

The MongoDB Service forwards traffic to the MongoDB pod on port `27017`.

The `mongodb-headless` Service is associated with the MongoDB StatefulSet and provides stable network identity.

The database is not exposed externally through a NodePort or LoadBalancer.

## Resource Management

Both Flask and MongoDB containers have resource requests and limits.

| Resource | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---|---:|---:|---:|---:|
| Flask | 200m | 500m | 250Mi | 500Mi |
| MongoDB | 200m | 500m | 250Mi | 500Mi |

Requests help Kubernetes schedule workloads based on available node resources.

Limits prevent containers from exceeding their configured CPU and memory allocations. CPU usage can be throttled at its limit, while exceeding the memory limit can result in an OOM kill.

The Flask HPA calculates CPU utilization relative to the CPU request.

## Persistent Storage

MongoDB stores its data at:

```text
/data/db
```

This directory is mounted from the `mongodb-pvc` PersistentVolumeClaim.

Storage configuration:

| Property | Value |
|---|---|
| Volume size | 1 GiB |
| Access mode | ReadWriteOnce |
| Storage class | manual |
| Reclaim policy | Retain |
| Volume type | hostPath |

The `Retain` reclaim policy helps preserve the underlying volume data when the claim is released.

The project was tested by recreating the MongoDB pod and verifying that previously inserted documents remained available.

Note: The `hostPath` volume is intended for this Minikube environment. A production deployment should use an appropriate persistent storage provisioner.

## Health Checks

The Flask Deployment uses HTTP health probes against `/` on port `5000`.

MongoDB uses TCP socket probes against port `27017`:

- **Startup probe:** Allows MongoDB time to start before other probes take over.
- **Readiness probe:** Checks whether the MongoDB port is accepting TCP connections.
- **Liveness probe:** Checks whether the MongoDB process is responding on its port.

TCP probes avoid repeatedly launching `mongosh` processes for health checks.

These probes verify process/network availability, not full database authentication or query functionality.

## Load Testing and Autoscaling Results

A concurrent load generator was deployed inside Kubernetes to send repeated HTTP requests to the Flask Service.

Load generator command:

```powershell
kubectl run flask-load-generator `
  --namespace flask-mongodb `
  --image=busybox:1.36 `
  --restart=Never `
  --command -- sh -c 'for i in $(seq 1 20); do (while true; do wget -q -O /dev/null http://flask-service:5000/; done) & done'
```

Monitor HPA:

```powershell
kubectl get hpa -n flask-mongodb -w
```

Monitor Flask replicas:

```powershell
kubectl get deployment flask-app -n flask-mongodb -w
```

### Observed Results

| Metric | Observed Result |
|---|---:|
| Configured CPU target | 70% |
| CPU utilization under load | 114% |
| Initial Flask replicas | 2 |
| Replicas after scale-up | 4 |
| Maximum replicas configured | 5 |
| CPU after load stopped | 1% |
| Final Flask replicas | 2 |
| MongoDB restarts during final test | 0 |

The HPA generated successful rescaling events:

```text
SuccessfulRescale
New size: 4
reason: cpu resource utilization above target
```

After the load generator was stopped:

```text
SuccessfulRescale
New size: 2
reason: All metrics below target
```

This demonstrated both horizontal scale-up and scale-down.

Stop the load generator:

```powershell
kubectl delete pod flask-load-generator -n flask-mongodb
```

### Useful Monitoring Commands

```powershell
kubectl get pods -n flask-mongodb

kubectl get services -n flask-mongodb

kubectl get deployments -n flask-mongodb

kubectl get statefulsets -n flask-mongodb

kubectl get pvc -n flask-mongodb

kubectl get hpa -n flask-mongodb

kubectl top pods -n flask-mongodb

kubectl describe hpa flask-hpa -n flask-mongodb
```

## Design Decisions

### Why a StatefulSet for MongoDB?

MongoDB requires stable pod identity and persistent storage. A StatefulSet provides stable identity and works with persistent volume claims.

### Why a Deployment for Flask?

The Flask API is stateless at the application layer. Multiple interchangeable replicas can serve incoming requests, making a Deployment suitable for horizontal scaling.

### Why separate Services?

The Flask NodePort Service provides external access to the API, while the MongoDB ClusterIP Service keeps database communication internal to the cluster.

### Why Kubernetes Secrets?

MongoDB credentials and the application connection URI are injected through Secrets rather than being hardcoded in the application Deployment.

### Why HPA?

HPA automatically adjusts the Flask replica count based on CPU utilization, allowing the application to respond to changing workloads.

### Why resource requests and limits?

They provide predictable scheduling and resource boundaries for both application and database containers.

## Limitations and Future Improvements

- MongoDB currently runs with one replica; it is not a highly available replica set.
- The `hostPath` volume is suitable for local Minikube testing, not portable production storage.
- Kubernetes Secrets are used for configuration, but production deployments should also configure encryption at rest and stricter access controls.
- The Flask API currently has no authentication or authorization layer.
- Production deployments should use TLS, ingress, monitoring, centralized logging, and more comprehensive health checks.
- The current load test demonstrates autoscaling behavior, not a formal throughput or latency benchmark.

## Author

Developed as a Flask, MongoDB, Docker, and Kubernetes deployment assignment.

**Docker Hub Image:** `theakshatraj/flask-mongodb-kubernetes:v1`
