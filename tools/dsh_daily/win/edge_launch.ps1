param([string]$Port = '9223', [string]$Profile = 'C:\Users\eamon\edge-capture')
$exe = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Where-Object {
  $_.CommandLine -and $_.CommandLine -like "*$Profile*" -and $_.CommandLine -notlike '*--type=*'
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 400
$cmd = '"' + $exe + '" --headless=new --no-sandbox --no-first-run --disable-gpu-sandbox ' +
       '--use-gl=angle --use-angle=d3d11 --hide-scrollbars ' +
       '--autoplay-policy=no-user-gesture-required --disable-background-timer-throttling ' +
       '--disable-renderer-backgrounding --disable-backgrounding-occluded-windows ' +
       '--window-size=1920,1080 --remote-debugging-port=' + $Port + ' ' +
       '--user-data-dir="' + $Profile + '" about:blank'
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
"launched pid $($r.ProcessId) rc $($r.ReturnValue)"
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 500
  try { $v = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 2; break } catch { }
}
if ($v) { 'CDP_OK ' + $v.Browser } else { 'CDP_FAIL' }
