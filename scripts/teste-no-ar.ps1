# Teste no ar - smoke end-to-end da CDA com processo real de API.
# Sobe uvicorn, valida login + R5 + R4 + constituicao + health, REINICIA
# o processo com o mesmo CDA_STATE_DIR e confere o replay do ledger.
# Uso: powershell -File scripts\teste-no-ar.ps1 [-Port 8111]
param(
    [string]$Port = "8111",
    [string]$StateDir = "$env:TEMP\viableos-smoke-estado"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

# ambiente (herdado pelo processo filho)
$env:PYTHONPATH = Join-Path $RepoRoot "src"
$env:CDA_STATE_DIR = $StateDir
$env:USERS_JSON = Join-Path $RepoRoot "users.dev.json"
$env:JWT_SECRET_KEY = "viableos-dev-insecure-change-me"

if (Test-Path $StateDir) { Remove-Item -Recurse -Force $StateDir }
$log = "$env:TEMP\viableos-smoke-api.log"
Remove-Item "$log","$log.err" -ErrorAction SilentlyContinue

function Start-API {
    Start-Process -FilePath "python" `
        -ArgumentList "-m","uvicorn","viableos.api.main:app","--host","127.0.0.1","--port",$Port `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
        -PassThru -NoNewWindow
}

function Wait-Health([int]$Segundos = 25) {
    for ($i = 0; $i -lt $Segundos; $i++) {
        Start-Sleep -Milliseconds 700
        try {
            $h = Invoke-RestMethod "$script:Base/health" -TimeoutSec 3
            if ($h.status -eq "ok") { return }
        } catch {}
        if ($script:Proc.HasExited) {
            Get-Content "$log.err" -ErrorAction SilentlyContinue | Select-Object -Last 15 | Write-Host
            throw "API morreu durante o boot (log: $log.err)"
        }
    }
    throw "API nao subiu em $Segundos segundos"
}

function Post([string]$Path, $Body, [hashtable]$Headers = @{}) {
    try {
        $json = $Body | ConvertTo-Json -Depth 8
        $resp = Invoke-WebRequest -Method Post -Uri "$script:Base$Path" `
            -ContentType "application/json; charset=utf-8" -Body $json `
            -Headers $Headers -UseBasicParsing -TimeoutSec 15
        $text = [System.Text.Encoding]::UTF8.GetString($resp.RawContentStream.ToArray())
        return ($text | ConvertFrom-Json)
    } catch [System.Net.WebException] {
        $code = [int]$_.Exception.Response.StatusCode
        return [pscustomobject]@{ _http = $code }
    }
}

# PS 5.1 decoda JSON sem charset como Latin-1; forcamos UTF-8 no cliente.
function Get-J([string]$Path) {
    if (-not $Path.StartsWith("http")) { $Path = "$script:Base$Path" }
    $resp = Invoke-WebRequest -Uri $Path -UseBasicParsing -TimeoutSec 15
    $text = [System.Text.Encoding]::UTF8.GetString($resp.RawContentStream.ToArray())
    return ($text | ConvertFrom-Json)
}

$script:Base = "http://127.0.0.1:$Port"
$script:Proc = $null
$passo = 0
function Passo([string]$Msg) {
    $script:passo++
    Write-Host ("[{0:d2}] {1}" -f $script:passo, $Msg) -ForegroundColor Green
}

try {
    # ================= BOOT 1 =================
    $script:Proc = Start-API
    Wait-Health
    Passo "API no ar na porta $Port"

    # --- login (fluxo documentado /api/auth/login + bcrypt) ---
    $login = Post "/api/auth/login" @{ username = "admin"; password = "admin123" }
    if (-not $login.access_token) { throw "login falhou: $($login | ConvertTo-Json)" }
    Passo "POST /api/auth/login com admin/admin123 -> token JWT emitido"
    $auth = @{ Authorization = "Bearer $($login.access_token)" }

    # --- ledger ativo e vazio: seed demo fica desligado ---
    $pend = Get-J "$script:Base/api/cda/decisoes"
    if (@($pend).Count -ne 0) { throw "com CDA_STATE_DIR ativo o seed demo nao deveria rodar (achei $(@($pend).Count) pendentes)" }
    Passo "ledger ativo: seed demo desligado (0 pendentes)"

    # --- nome real do agente S4 via API (sem depender de encoding) ---
    $agentes = Get-J "$script:Base/api/cda/agentes"
    $nomeS4 = ($agentes | Where-Object { $_.nome -like "*S4*" } | Select-Object -First 1).nome
    if (-not $nomeS4) { throw "agente S4 nao encontrado na arvore" }
    $s4enc = [uri]::EscapeDataString($nomeS4)
    Passo "agente alvo: '$nomeS4'"

    # --- criar decisao via API com cascata R6 completa ---
    $d = Post "/api/cda/agentes/$s4enc/decisao" @{
        assunto = "Decisao do teste no ar"
        contexto = "Smoke end-to-end com processo real"
        opcoes = @("Opcao A", "Opcao B")
        justificativa = "Regra 2 do handout: intencao persiste fora do runner."
    }
    if ($d.status -ne "ok") { throw "criar decisao falhou: $($d | ConvertTo-Json)" }
    $decisaoId = $d.decisao_id
    Passo "POST decisao via API com cascata R6 completa -> id $decisaoId"

    # --- R6: sem cascata rejeitado ---
    $r = Post "/api/cda/agentes/$s4enc/decisao" @{ assunto = "incompleto" }
    if ($r.status -ne "erro" -or $r.motivo -notmatch "R6") { throw "decisao sem cascata deveria ser rejeitada com R6: $($r | ConvertTo-Json)" }
    Passo "R6 imposta: solicitar sem cascata completa rejeitado na entrada"

    # --- R5: resolver sem token -> 401 ---
    $r = Post "/api/cda/decisoes/$decisaoId/resolver" @{ resolucao = "Concluir sprint 3 com equipe atual" }
    if ($r._http -ne 401) { throw "resolver sem token deveria dar 401, deu $($r._http)" }
    Passo "R5 imposta: resolver sem token -> 401"

    # --- R5: resolver com token -> identidade do JWT ---
    $r = Post "/api/cda/decisoes/$decisaoId/resolver" @{ resolucao = "Concluir sprint 3 com equipe atual"; resolvido_por = "Impostor" } $auth
    if ($r.status -ne "ok") { throw "resolver com token falhou: $($r | ConvertTo-Json)" }
    $hist = Get-J "$script:Base/api/cda/decisoes/historico"
    $resolvida = @($hist | Where-Object { $_.id -eq $decisaoId })[0]
    if ($resolvida.resolvido_por -ne "admin") { throw "identidade registrada deveria ser 'admin' (JWT), e nao '$($resolvida.resolvido_por)'" }
    Passo "R5 com token OK - resolvido_por='$($resolvida.resolvido_por)' (do JWT; payload 'Impostor' ignorado); papel=$($resolvida.papel_aprovacao)"

    # --- R4: gatilho fora da tabela rejeitado ---
    $r = Post "/api/cda/sinais" @{ fonte = $nomeS4; gravidade = "amarelo"; assunto = "x"; mensagem = "x"; gatilho = "inventado" }
    if ($r.status -ne "erro" -or $r.motivo -notmatch "R4") { throw "gatilho invalido deveria ser rejeitado com R4: $($r | ConvertTo-Json)" }
    Passo "R4 imposta: sinal com gatilho 'inventado' rejeitado na entrada"

    # --- Constituicao acessivel (path corrigido) ---
    $const = Get-J "$script:Base/api/cda/constituicao"
    if ($const.conteudo -notmatch "R4") { throw "constituicao ausente ou sem R4" }
    Passo "GET /api/cda/constituicao retorna a Constituicao S5"

    # --- Health/boot com checks reais ---
    $boot = Get-J "$script:Base/api/cda/health/boot"
    if (@($boot.itens).Count -lt 6) { throw "health/boot vazio - checks nao rodaram" }
    Passo "health/boot executa $($boot.itens.Count) checks sobre os dados reais"

    # --- Discordancia como dado ---
    $disc = Get-J "$script:Base/api/cda/auditoria/discordancia"
    Passo "GET /api/cda/auditoria/discordancia -> taxa=$($disc.taxa) ($($disc.discordantes)/$($disc.total_analisadas))"

    Stop-Process -Id $script:Proc.Id -Force -ErrorAction SilentlyContinue
    Wait-Process -Id $script:Proc.Id -Timeout 10 -ErrorAction SilentlyContinue
    Passo "API morta (kill). Estado em: $StateDir"

    # ================= BOOT 2: restart real com replay =================
    $script:Proc = Start-API
    Wait-Health
    Passo "API reiniciada com o MESMO CDA_STATE_DIR"

    $hist2 = Get-J "$script:Base/api/cda/decisoes/historico"
    $sobreviveu = @($hist2 | Where-Object { $_.id -eq $decisaoId })
    if ($sobreviveu.Count -ne 1) { throw "decisao resolvida nao sobreviveu ao restart (replay falhou)" }
    if ($sobreviveu[0].resolvido_por -ne "admin") { throw "proveniencia da resolucao perdida no restart" }
    Passo "replay OK: decisao voltou resolvida por '$($sobreviveu[0].resolvido_por)'"

    $pend2 = Get-J "$script:Base/api/cda/decisoes"
    if (@($pend2).Count -ne 0) { throw "restart trouxe $(@($pend2).Count) pendentes inesperadas" }
    Passo "nenhuma pendente fantasma apos restart (replay fiel)"

    $led = Join-Path $StateDir "ledger_cda.jsonl"
    $linhas = (Get-Content $led | Measure-Object -Line).Lines
    Passo "ledger $led -> $linhas registros"

    Write-Host ""
    Write-Host "==== TESTE NO AR: TODOS OS PASSOS PASSARAM ====" -ForegroundColor Cyan
} finally {
    if ($script:Proc -and -not $script:Proc.HasExited) {
        Stop-Process -Id $script:Proc.Id -Force -ErrorAction SilentlyContinue
    }
}
