# Inventory of dsh builds and sessions on the Windows box.
# Emits one JSON object on stdout. Reads no state.
$root      = 'C:\Users\Eamon\Desktop\Model Testing'
$sessions  = 'C:\Users\Eamon\.dsh\sessions'
$sinceTxt  = if ($args.Count -gt 0 -and $args[0]) { $args[0] } else { '2000-01-01T00:00:00' }
$since     = [datetime]::Parse($sinceTxt)

$builds = @()
Get-ChildItem $root -Recurse -Filter *.html -File | Where-Object { $_.LastWriteTime -gt $since } | ForEach-Object {
  $rel = $_.FullName.Substring($root.Length + 1)
  $head = ''
  try { $head = (Get-Content $_.FullName -TotalCount 4 -ErrorAction Stop) -join "`n" } catch { }
  $builds += [pscustomobject]@{
    rel        = $rel
    bytes      = $_.Length
    mtime      = $_.LastWriteTime.ToString('yyyy-MM-ddTHH:mm:ss')
    doctype    = ($head -match '<!DOCTYPE html')
  }
}

$sess = @()
Get-ChildItem $sessions -Recurse -Filter 'session.v4.jsonl.zstd' -File | Where-Object { $_.LastWriteTime -gt $since } | ForEach-Object {
  $sess += [pscustomobject]@{
    ws     = $_.Directory.Parent.Name
    uuid   = $_.Directory.Name -replace '^session-', ''
    bytes  = $_.Length
    mtime  = $_.LastWriteTime.ToString('yyyy-MM-ddTHH:mm:ss')
    rel    = $_.FullName.Substring($sessions.Length + 1)
  }
}

[pscustomobject]@{
  now      = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')
  desktop  = [Environment]::GetFolderPath('Desktop')
  builds   = $builds
  sessions = $sess
} | ConvertTo-Json -Depth 4 -Compress
