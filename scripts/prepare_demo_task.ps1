param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9_-]{1,64}$')]
    [string]$SessionId,
    [string]$PythonPath = '',
    [string]$RiskProfile = 'risk-demo.json',
    [switch]$ExecuteDemo
)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $PythonPath) { $PythonPath = (Get-Command python -CommandType Application).Source }
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
if (-not [IO.Path]::IsPathRooted($RiskProfile)) { $RiskProfile = Join-Path $taskRoot $RiskProfile }
$RiskProfile = (Resolve-Path -LiteralPath $RiskProfile).Path
$taskArguments = '-m agentrader service run "' + $SessionId + '" --risk-profile "' + $RiskProfile + '" --interval 5 --user-stream'
if ($ExecuteDemo) { $taskArguments += ' --execute-demo' }
$taskUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$taskAction = New-ScheduledTaskAction -Execute $PythonPath -Argument $taskArguments -WorkingDirectory $taskRoot
$taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUser
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
# No automatic restart loop: an uncertain exchange write requires reconciliation.
$taskSettings = New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$taskDefinition = New-ScheduledTask -Action $taskAction -Trigger $taskTrigger -Principal $taskPrincipal -Settings $taskSettings -Description 'Existing demo session only; never creates a new trading plan.'
$taskOutput = Join-Path $taskRoot 'reports\demo-service-task.xml'
$taskXml = Export-ScheduledTask -InputObject $taskDefinition
Set-Content -LiteralPath $taskOutput -Value $taskXml -Encoding Unicode
Write-Output ('Prepared task XML: ' + $taskOutput)
Write-Output 'No task was registered or started. The default task is read-only.'
