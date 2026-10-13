# Auto-commit com debounce - vigia o repo e commita apos N segundos de quietude.
# Objetivo: checkpoint continuo sem "tiltar" o sistema (nao commita enquanto
# arquivos ainda estao mudando) e sem risco de vazar secret.
#
# Uso (cmd, dentro da pasta do repo):
#   powershell -ExecutionPolicy Bypass -File scripts\auto-commit-watch.ps1
#
# Opcoes:
#   -DelaySegundos 90      quietude necessaria antes de commitar (default 60)
#   -IntervaloSegundos 10  frequencia de checagem (default 10)
#   -Push                  tambem faz pull --rebase + push (default: so commit local)
#   -Repo "C:\outro\repo"  repo a vigiar (default: a pasta PAI deste script)
#
# Parar: Ctrl+C na janela. Log em %TEMP%\auto-commit-watch.log
param(
    [int]$DelaySegundos = 60,
    [int]$IntervaloSegundos = 10,
    [switch]$Push,
    [string]$Repo = ""
)

$ErrorActionPreference = "Continue"
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }
$log = Join-Path $env:TEMP "auto-commit-watch.log"

function Logar([string]$Msg) {
    $linha = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
    Write-Host $linha
    Add-Content -Path $log -Value $linha
}

Write-Host "Vigiando: $Repo" -ForegroundColor Cyan
Write-Host "Quietude: ${DelaySegundos}s | Checagem: ${IntervaloSegundos}s | Push: $($Push.IsPresent) | Log: $log" -ForegroundColor Cyan
Logar "watcher iniciado em '$Repo' (delay=$DelaySegundos s, intervalo=$IntervaloSegundos s, push=$($Push.IsPresent))"

$ultimaMudanca = $null
$ultimaAssinatura = ""

while ($true) {
    Start-Sleep -Seconds $IntervaloSegundos

    $status = & git -C $Repo status --porcelain 2>$null
    if ($null -eq $status) { $status = @() }
    $assinatura = ($status | Out-String)

    # mudou algo? reinicia o cronometro de quietude
    if ($assinatura -ne $ultimaAssinatura) {
        if ($ultimaAssinatura -ne "" -and $assinatura.Trim() -ne "") { Logar "mudanca detectada, aguardando quietude..." }
        $ultimaAssinatura = $assinatura
        $ultimaMudanca = Get-Date
        continue
    }

    if ($assinatura.Trim() -eq "") { continue }          # nada a commitar
    if ($null -eq $ultimaMudanca) { continue }

    $quietoSeg = ((Get-Date) - $ultimaMudanca).TotalSeconds
    if ($quietoSeg -lt $DelaySegundos) { continue }      # ainda mexendo

    $n = ($status | Measure-Object).Count
    & git -C $Repo add -A 2>&1 | Out-Null

    # GUARDA ANTI-SECRET: aborta se algo sensivel entrou no stage.
    # NUNCA commitar: .env (exceto .example), *.pem, *.key, *secret*, *credential*, id_rsa
    $staged = & git -C $Repo diff --cached --name-only 2>$null
    $suspeitos = @($staged | Where-Object {
        ($_ -match "(?i)(secret|credential|id_rsa|\.pem$|\.key$)") -or
        ($_ -match "(?i)\.env" -and $_ -notmatch "(?i)\.example$")
    })
    if ($suspeitos.Count -gt 0) {
        Logar "ABORTADO: arquivo(s) suspeito(s) de secret no stage -> $($suspeitos -join ', ')"
        & git -C $Repo reset 2>&1 | Out-Null
        $ultimaMudanca = Get-Date
        continue
    }

    $msg = "auto: {0} ({1} arquivos)" -f (Get-Date -Format "yyyy-MM-dd HH:mm"), $n
    & git -C $Repo commit -q -m $msg 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Logar "commit: $msg"
        if ($Push) {
            & git -C $Repo pull --rebase --autostash 2>&1 | Out-Null
            & git -C $Repo push 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { Logar "push ok" }
            else { Logar "push falhou (commit local preservado; resolva depois)" }
        }
    } else {
        Logar "commit nao realizado (nada util ou erro)"
    }

    $ultimaAssinatura = ""
    $ultimaMudanca = $null
}
