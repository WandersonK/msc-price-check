# Gatilho externo (cron-job.org → GitHub Actions)

O `schedule` do GitHub é instável (atrasa e descarta execuções). Para garantir
que o monitor rode de hora em hora, usamos um cron externo gratuito que dispara
o workflow via `workflow_dispatch` na API do GitHub.

O `schedule` no `check.yml` fica como **backup** (1x/hora).

---

## 1. Criar o token do GitHub (fine-grained)

1. Acesse: https://github.com/settings/personal-access-tokens/new
2. **Token name:** `disparo-msc-price-check`
3. **Expiration:** 1 ano (ou "No expiration" se preferir menos manutenção)
4. **Resource owner:** WandersonK
5. **Repository access:** *Only select repositories* → marque `msc-price-check`
6. **Permissions → Repository permissions:**
   - **Actions**: `Read and write`
   - (o `Metadata: Read-only` é adicionado sozinho)
7. Clique em **Generate token** e **copie o valor** (`github_pat_...`).
   Ele só aparece uma vez.

> Guarde esse token com segurança. Ele permite disparar o workflow.

---

## 2. Configurar o cron-job.org

1. Crie conta gratuita em https://cron-job.org e faça login.
2. **Create cronjob**.
3. **Title:** `Disparar MSC Price Check`
4. **URL:**
   ```
   https://api.github.com/repos/WandersonK/msc-price-check/actions/workflows/check.yml/dispatches
   ```
5. **Schedule:** *Every 1 hour* (ou o horário desejado). Sugestão: minuto 17.
6. Abra **Advanced settings**:
   - **Request method:** `POST`
   - **Request headers** (adicione um por um):
     | Nome | Valor |
     |------|-------|
     | `Accept` | `application/vnd.github+json` |
     | `Authorization` | `Bearer COLE_SEU_TOKEN_AQUI` |
     | `X-GitHub-Api-Version` | `2022-11-28` |
     | `User-Agent` | `cron-job.org` |
   - **Request body:**
     ```json
     {"ref":"main"}
     ```
7. **Save**.

> Resposta esperada da API: **HTTP 204 No Content** (sucesso, sem corpo).
> No cron-job.org o job aparecerá como sucesso (2xx).

---

## 3. Testar imediatamente

No cron-job.org, use **"Run now"** (ou "Test run"). Em seguida confira em:
https://github.com/WandersonK/msc-price-check/actions

Deve aparecer uma execução nova do workflow "Monitorar preço MSC".

---

## Teste manual pelo terminal (opcional)

PowerShell:
```powershell
$token = "COLE_SEU_TOKEN_AQUI"
Invoke-RestMethod -Method Post `
  -Uri "https://api.github.com/repos/WandersonK/msc-price-check/actions/workflows/check.yml/dispatches" `
  -Headers @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "local-test"
  } `
  -Body '{"ref":"main"}'
```
Sucesso = nenhum erro / status 204.

---

## Observações

- Se o token expirar, o cron-job.org passa a receber **401**. Basta gerar um
  token novo e atualizar o header `Authorization`.
- O endpoint usa o nome do arquivo do workflow (`check.yml`). Se renomear o
  arquivo, atualize a URL.
- `{"ref":"main"}` = dispara usando o branch `main`.
