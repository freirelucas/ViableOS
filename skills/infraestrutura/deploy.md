# Deploy — Corporação Virtual DIEST

## Arquitetura de Produção

```
                    Internet
                       │
                  [Proxy IPEA]
                       │
              ┌────────┴────────┐
              │                 │
        nginx reverso    ipeagpt.ipea.gov.br
        (porta 443)      (LLM API)
              │
       ┌──────┴──────┐
       │             │
    Frontend       API
    (nginx)     (uvicorn)
    :3000        :8000
       │             │
       └──────┬──────┘
              │
         [Docker Compose]
```

## Docker Compose (já configurado)

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - USERS_JSON=/app/users.json
      - IPEAGPT_URL=https://ipeagpt.ipea.gov.br/api/v1
    volumes:
      - ./users.prod.json:/app/users.json:ro

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - api
```

## Produção IPEA

### Requisitos
1. Docker instalado no servidor IPEA (ou Windows com Docker Desktop)
2. Proxy configurado para internet
3. Certificado SSL para HTTPS
4. Usuários reais no `users.prod.json` (hashes bcrypt)

### Build
```bash
# Backend
docker build -t viableos-api -f Dockerfile.api .
# Frontend
docker build -t viableos-frontend ./frontend
# Subir
docker compose up -d
```

### Sem Docker (Windows direto)
```powershell
# Terminal 1 - API
$env:JWT_SECRET_KEY="<segredo>"
$env:USERS_JSON=".\users.prod.json"
python -m uvicorn viableos.api.main:app --host 10.100.33.75 --port 8000

# Terminal 2 - Frontend (dev)
cd frontend
npm run dev -- --host 10.100.33.75
```

### Proxy Reverso (se necessário)
```nginx
server {
    listen 443 ssl;
    server_name viableos.ipea.gov.br;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

## Segurança
- JWT com bcrypt para senhas
- API key do GLM em variável de ambiente (nunca em código)
- CORS limitado aos domínios do IPEA
- Logs centralizados (ELK ou similar)
- Backup dos dados de configuração dos VSMs
