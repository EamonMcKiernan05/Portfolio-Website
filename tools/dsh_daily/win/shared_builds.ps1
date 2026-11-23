# Keep the shared-builds folder on the Desktop in sync with the gallery.
#   shared_builds.ps1 list                 -> JSON list of every recorded clip
#   shared_builds.ps1 apply <zip> <json>   -> refresh the folder in place
# Runs are cheap when nothing changed: clips are only copied when the size differs, and files
# that no longer belong to a build (withdrawn builds, replaced takes) are pruned.
$vids = 'C:\Users\eamon\Desktop\Model Testing Videos'
$dest = 'C:\Users\eamon\Desktop\Model Testing - Shared Builds'
$mode = if ($args.Count -gt 0 -and $args[0]) { $args[0] } else { 'list' }

if ($mode -eq 'list') {
  $out = @()
  if (Test-Path $vids) {
    Get-ChildItem $vids -Recurse -Filter *.mp4 -File | ForEach-Object {
      $out += [pscustomobject]@{
        rel   = $_.FullName.Substring($vids.Length + 1)
        name  = $_.Name
        bytes = $_.Length
      }
    }
  }
  ConvertTo-Json -InputObject @($out) -Compress
  return
}

$zip = $args[1]
$man = $args[2]
if (-not (Test-Path $zip)) { "ERROR zip missing: $zip"; return }
if (-not (Test-Path $man)) { "ERROR manifest missing: $man"; return }

if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
Expand-Archive -Path $zip -DestinationPath $dest -Force

$m = Get-Content $man -Raw | ConvertFrom-Json
$copied = 0
$same = 0
$missing = @()
$wanted = @{}
$names = @()

foreach ($b in @($m.builds)) {
  $names += $b.name
  $dir = Join-Path $dest $b.name
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  $keep = @()
  foreach ($h in @($b.html)) { $keep += $h }
  foreach ($c in @($b.clips)) {
    $keep += $c.as
    $from = Join-Path $vids $c.rel
    $to = Join-Path $dir $c.as
    if (-not (Test-Path $from)) { $missing += $c.rel; continue }
    if ((Test-Path $to) -and (Get-Item $to).Length -eq (Get-Item $from).Length) { $same++; continue }
    Copy-Item $from $to -Force
    $copied++
  }
  $wanted[$dir] = $keep
}

# prune anything that no longer belongs
$pruned = 0
Get-ChildItem $dest -Directory | ForEach-Object {
  if ($names -notcontains $_.Name) { Remove-Item $_.FullName -Recurse -Force; $pruned++ }
}
foreach ($dir in $wanted.Keys) {
  Get-ChildItem $dir -File | ForEach-Object {
    if ($wanted[$dir] -notcontains $_.Name) { Remove-Item $_.FullName -Force; $pruned++ }
  }
}

$builds = @(Get-ChildItem $dest -Directory | Sort-Object Name | ForEach-Object {
  [pscustomobject]@{
    name = $_.Name
    html = @(Get-ChildItem $_.FullName -Filter *.html -File).Count
    mp4  = @(Get-ChildItem $_.FullName -Filter *.mp4 -File).Count
  }
})
ConvertTo-Json -InputObject ([pscustomobject]@{
  dest    = $dest
  builds  = $builds
  html    = @(Get-ChildItem $dest -Recurse -Filter *.html -File).Count
  mp4     = @(Get-ChildItem $dest -Recurse -Filter *.mp4 -File).Count
  copied  = $copied
  unchanged = $same
  pruned  = $pruned
  missing = @($missing)
}) -Depth 4 -Compress
