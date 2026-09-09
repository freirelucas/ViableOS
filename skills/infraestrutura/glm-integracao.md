# GLM 5.2 — Integração com ViableOS

## Endpoint
```
POST https://ipeagpt.ipea.gov.br/api/v1/chat/completions
```

## Autenticação
Requires API key no header:
```
Authorization: Bearer sk-xxx...
```

## Parâmetros

| Parâmetro | Valor Fixo | Notas |
|-----------|-----------|-------|
| `model` | `glm-5-52b-0106` | GLM 5.2 para todos os agentes |
| `temperature` | `0.7` | Balança criatividade/precisão |
| `max_tokens` | `4096` | Suficiente para pareceres e textos |
| `stream` | `false` | (true para chat streaming) |

## System Prompt Padrão para Agentes VSM

```
Você é {nome do agente} na {nível} do Viable System Model da DIEST/IPEA.

Propósito: {propósito}

Valores: {valores}

Limites (nunca faça):
{never_do}

Autonomia:
- Pode fazer sozinho: {can_do_alone}
- Precisa coordenar: {needs_coordination}
- Precisa aprovação: {needs_approval}

Ferramentas disponíveis:
{tools}

Contexto atual:
{situação}

Histórico da conversa:
{history}
```

## Rate Limits
- Modelo GLM 5.2: ~60 req/min (confirmar com administrador)
- Cache de respostas comuns implementar no ViableOS
- Fallback: nenhum (só GLM, conforme decisão do projeto)

## Proxy
Se o servidor ViableOS estiver atrás do proxy corporativo IPEA:
```
HTTP_PROXY=http://10.1.200.104:3128
HTTPS_PROXY=http://10.1.200.104:3128
```

## Implementação no ViableOS
- `src/viableos/chat/engine.py` — LiteLLM já configurado para múltiplos providers
- Adicionar configuração do IpeaGPT como um provider LiteLLM customizado
- Ou implementar chamada direta via `httpx` se LiteLLM não suportar GLM

```python
# Exemplo de chamada direta
import httpx

async def glm_chat(system_prompt: str, user_message: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://ipeagpt.ipea.gov.br/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": "glm-5-52b-0106",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )
        return resp.json()["choices"][0]["message"]["content"]
```
