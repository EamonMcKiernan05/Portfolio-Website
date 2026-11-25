param([string]$Url)
# The box captures the video, so the page has to be reachable from the bolt: a page it cannot
# load records a perfect 60 s of the browser's error screen.
try {
  $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 20
  "$($r.StatusCode)|$($r.RawContentLength)"
} catch {
  "ERR|$($_.Exception.Message)"
}
