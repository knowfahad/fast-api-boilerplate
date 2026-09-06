# Deploying to EKS

Full walkthrough to ship the image to Amazon EKS with a Deployment, Service, and an
ALB Ingress. Placeholders to replace: `<account-id>`, `<region>`, `<cluster>`,
`fahad.example.com`.

## Prerequisites

- An EKS cluster, plus the [AWS Load Balancer Controller][albc] installed (for the
  ALB Ingress).
- `awscli`, `kubectl`, and Docker.
- An ECR repository named `fahad`.

## 1. Get Kubernetes access

```bash
aws eks update-kubeconfig --region <region> --name <cluster>
kubectl config current-context
kubectl get nodes                     # confirm access
```

## 2. Build and push the image to ECR

Build for `linux/amd64` explicitly if you are on Apple Silicon.

```bash
export AWS_REGION=<region> AWS_ACCOUNT_ID=<account-id>
export ECR=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
export IMAGE=$ECR/fahad:v1

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ECR

docker build --platform linux/amd64 -t $IMAGE .
docker push $IMAGE
```

## 3. Manifests

The manifests live in `deployment/` (`configmap.yaml`, `deployment.yaml`,
`service.yaml`, `ingress.yaml`). Set `image:` in `deployment/deployment.yaml` to the
tag you pushed, plus the Ingress `host:`. The block below is the same content for
reference.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fahad-config
data:
  APP_NAME: fahad
  HOST: "0.0.0.0"
  PORT: "8000"
  WORKERS: "2"
  LOG_LEVEL: info
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fahad
  labels:
    app: fahad
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fahad
  template:
    metadata:
      labels:
        app: fahad
    spec:
      containers:
        - name: api
          image: <account-id>.dkr.ecr.<region>.amazonaws.com/fahad:v1
          ports:
            - name: http
              containerPort: 8000
          envFrom:
            - configMapRef:
                name: fahad-config
          readinessProbe:
            httpGet:
              path: /openapi.json
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /openapi.json
              port: http
            initialDelaySeconds: 10
            periodSeconds: 15
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          securityContext:
            runAsNonRoot: true
            runAsUser: 1001
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
---
apiVersion: v1
kind: Service
metadata:
  name: fahad
spec:
  selector:
    app: fahad
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fahad
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /openapi.json
spec:
  ingressClassName: alb
  rules:
    - host: fahad.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fahad
                port:
                  name: http
```

> Probes hit `/openapi.json` (always 200) so this works without a health route. Add
> a dedicated `/health` endpoint later and point the probes and
> `healthcheck-path` at it.

## 4. Apply and verify

```bash
kubectl apply -f deployment/
kubectl rollout status deployment/fahad
kubectl get pods -l app=fahad
kubectl get ingress fahad                 # wait for the ALB ADDRESS

# quick check without DNS:
kubectl port-forward svc/fahad 8000:80
curl -X POST http://localhost:8000/greetings \
  -H 'Content-Type: application/json' -d '{"name":"world"}'
```

Point your DNS (or a Route 53 alias) at the Ingress ADDRESS to serve
`fahad.example.com`.

## 5. Ship a new version

```bash
docker build --platform linux/amd64 -t $ECR/fahad:v2 .
docker push $ECR/fahad:v2
kubectl set image deployment/fahad api=$ECR/fahad:v2
kubectl rollout status deployment/fahad
kubectl rollout undo deployment/fahad      # if needed
```

## Notes

- **Secrets:** for anything sensitive (e.g. `DATABASE_URL` from `db.README.md`),
  use a `Secret` + `envFrom.secretRef` instead of the ConfigMap, or External
  Secrets / SSM.
- **TLS:** add `alb.ingress.kubernetes.io/certificate-arn` and
  `alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'` with an ACM cert.
- **Autoscaling:** add a `HorizontalPodAutoscaler` on CPU; keep `WORKERS` at 1-2
  and scale with replicas so the HPA is the single scaling signal.
- **Read-only rootfs:** the app writes nothing. If that changes, mount an
  `emptyDir` at `/tmp`.

[albc]: https://kubernetes-sigs.github.io/aws-load-balancer-controller/
