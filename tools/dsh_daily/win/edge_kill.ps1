param([string]$Profile = 'C:\Users\eamon\edge-capture')
$killed = 0
Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Where-Object {
  $_.CommandLine -and $_.CommandLine -like "*$Profile*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $killed++ }
"killed $killed processes for $Profile"
