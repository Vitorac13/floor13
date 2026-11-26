$ErrorActionPreference = 'Stop'
$out = $PSScriptRoot
function Save-Svg($name, $width, $height, $body) {
  $svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + $width + '" height="' + $height + '" viewBox="0 0 ' + $width + ' ' + $height + '" shape-rendering="crispEdges">' + $body + '</svg>'
  [System.IO.File]::WriteAllText((Join-Path $out $name), $svg, [System.Text.UTF8Encoding]::new($false))
}
function Rect($x,$y,$w,$h,$fill) { '<rect x="'+$x+'" y="'+$y+'" width="'+$w+'" height="'+$h+'" fill="'+$fill+'"/>' }

# Modular wall and floor tiles are deliberately small, so nearest-neighbor scaling stays sharp.
$wall = (Rect 0 0 64 64 '#202831') + (Rect 0 0 64 3 '#34434d') + (Rect 0 4 64 2 '#111921') +
  (Rect 0 29 64 2 '#101820') + (Rect 0 32 64 2 '#35444c') + (Rect 31 3 2 26 '#111921') +
  (Rect 0 61 64 3 '#101820') + (Rect 16 34 2 27 '#101820') + (Rect 49 34 2 27 '#111921') +
  (Rect 5 9 12 2 '#394854') + (Rect 39 47 8 2 '#3a4952') + (Rect 59 13 2 10 '#3b4650') +
  (Rect 24 53 4 2 '#52616a') + (Rect 12 24 2 2 '#65707a')
Save-Svg 'wall-tile.svg' 64 64 $wall
$floor = (Rect 0 0 64 32 '#303840') + (Rect 0 0 64 3 '#77848a') + (Rect 0 3 64 3 '#151d24') +
  (Rect 0 9 64 2 '#1a2229') + (Rect 0 16 64 2 '#171f26') + (Rect 0 25 64 2 '#171f26') +
  (Rect 31 9 2 23 '#131b21') + (Rect 0 30 64 2 '#11181d') + (Rect 5 12 13 2 '#45515a') +
  (Rect 39 20 10 2 '#46525a') + (Rect 56 12 3 2 '#788387')
Save-Svg 'floor-tile.svg' 64 32 $floor

$door = (Rect 2 4 44 74 '#0b1117') + (Rect 0 8 2 70 '#0d1319') + (Rect 46 8 2 70 '#0d1319') +
  (Rect 2 4 44 4 '#79868b') + (Rect 4 8 40 4 '#29353d') + (Rect 4 12 2 62 '#61727a') +
  (Rect 42 12 2 62 '#61727a') + (Rect 6 14 17 56 '#35434c') + (Rect 25 14 17 56 '#2b3942') +
  (Rect 8 16 3 50 '#53636c') + (Rect 27 16 3 50 '#45545c') + (Rect 22 14 4 56 '#0b1117') +
  (Rect 6 70 36 4 '#56656c') + (Rect 0 74 48 6 '#1a242b') + (Rect 7 0 34 4 '#d9f65a') +
  (Rect 13 1 22 2 '#f5ffb7') + (Rect 12 20 4 2 '#87959a') + (Rect 34 20 4 2 '#7b888d')
Save-Svg 'elevator.svg' 48 80 $door

function Character-Frame($offset,$pose) {
  $p = ''
  # Hair, face, coat, backpack, arms and boots. Each pose changes only limbs.
  $p += Rect ($offset+7) 2 11 3 '#17212a'
  $p += Rect ($offset+5) 5 15 6 '#17212a'
  $p += Rect ($offset+7) 8 11 8 '#d99470'
  $p += Rect ($offset+8) 10 2 2 '#17212a'
  $p += Rect ($offset+16) 10 2 2 '#17212a'
  $p += Rect ($offset+7) 15 12 3 '#9d624c'
  $p += Rect ($offset+4) 17 4 16 '#435463'
  $p += Rect ($offset+8) 17 11 17 '#d9f65a'
  $p += Rect ($offset+10) 19 3 12 '#f0ff8f'
  $p += Rect ($offset+17) 17 3 16 '#9bad40'
  if ($pose -eq 1) {
    $p += Rect ($offset+2) 18 3 11 '#d9f65a'; $p += Rect ($offset+19) 21 3 11 '#d9f65a'
    $p += Rect ($offset+7) 33 5 5 '#354757'; $p += Rect ($offset+15) 33 5 3 '#354757'
    $p += Rect ($offset+5) 38 7 2 '#111a23'; $p += Rect ($offset+15) 36 7 3 '#111a23'
  } elseif ($pose -eq 2) {
    $p += Rect ($offset+2) 21 3 11 '#d9f65a'; $p += Rect ($offset+19) 18 3 11 '#d9f65a'
    $p += Rect ($offset+8) 33 5 4 '#354757'; $p += Rect ($offset+14) 33 5 5 '#354757'
    $p += Rect ($offset+8) 37 7 2 '#111a23'; $p += Rect ($offset+14) 38 7 2 '#111a23'
  } else {
    $p += Rect ($offset+3) 19 3 12 '#d9f65a'; $p += Rect ($offset+20) 19 3 12 '#d9f65a'
    $p += Rect ($offset+8) 33 5 5 '#354757'; $p += Rect ($offset+15) 33 5 5 '#354757'
    $p += Rect ($offset+7) 38 7 2 '#111a23'; $p += Rect ($offset+15) 38 7 2 '#111a23'
  }
  return $p
}
$character = (Character-Frame 0 0) + (Character-Frame 24 1) + (Character-Frame 48 2) + (Character-Frame 72 1)
Save-Svg 'character-sheet.svg' 96 40 $character

function Icon($name,$body) {
  Save-Svg ($name+'.svg') 24 24 ((Rect 0 0 24 24 'none') + $body)
}
Icon 'item-key' ((Rect 2 7 9 9 '#e8c765')+(Rect 4 9 5 5 '#17222b')+(Rect 10 10 11 3 '#e8c765')+(Rect 17 13 3 5 '#e8c765')+(Rect 13 13 3 4 '#e8c765')+(Rect 2 7 9 2 '#fff0a0'))
Icon 'item-fuse' ((Rect 7 2 10 20 '#a5b9bd')+(Rect 9 0 6 3 '#e8c765')+(Rect 9 21 6 3 '#e8c765')+(Rect 9 5 6 14 '#e7b96a')+(Rect 11 7 2 10 '#fff2aa')+(Rect 8 13 8 2 '#5a7780'))
Icon 'item-card' ((Rect 2 5 20 15 '#83b8c8')+(Rect 4 7 16 11 '#d7e8df')+(Rect 4 8 16 3 '#394d60')+(Rect 6 14 5 2 '#d9f65a')+(Rect 14 14 4 2 '#7a9fa6'))
Icon 'item-paper' ((Rect 5 2 14 20 '#e4d7a8')+(Rect 7 4 10 16 '#f7edc7')+(Rect 9 8 6 2 '#6d7f83')+(Rect 9 12 7 2 '#6d7f83')+(Rect 9 16 5 2 '#6d7f83'))
Icon 'item-relic' ((Rect 8 2 8 4 '#dcb764')+(Rect 5 6 14 10 '#c58f48')+(Rect 7 8 10 6 '#f0d786')+(Rect 9 10 6 3 '#b4e1d4')+(Rect 8 16 8 5 '#947041')+(Rect 5 21 14 2 '#e9c773'))
Icon 'item-coin' ((Rect 5 3 14 18 '#c69345')+(Rect 7 5 10 14 '#f0d46e')+(Rect 10 7 4 10 '#bd883c')+(Rect 8 10 8 4 '#bd883c')+(Rect 11 8 2 8 '#ffe99a'))
Icon 'item-radio' ((Rect 3 8 18 13 '#465766')+(Rect 5 10 14 9 '#738c93')+(Rect 7 12 7 5 '#b5d8cf')+(Rect 16 13 3 3 '#e9c66a')+(Rect 6 3 2 6 '#d7c575')+(Rect 6 2 8 2 '#d7c575'))

$glyphs = @(
  @('111','101','101','101','111'), @('010','110','010','010','111'),
  @('111','001','111','100','111'), @('111','001','111','001','111'),
  @('101','101','111','001','001'), @('111','100','111','001','111'),
  @('111','100','111','101','111'), @('111','001','001','001','001'),
  @('111','101','111','101','111'), @('111','101','111','001','111')
)
for ($d=0; $d -lt 10; $d++) {
  $body = ''
  for ($y=0; $y -lt 5; $y++) {
    for ($x=0; $x -lt 3; $x++) {
      if ($glyphs[$d][$y][$x] -eq '1') { $body += Rect ($x+1) ($y+1) 1 1 '#d9f65a' }
    }
  }
  Save-Svg ('digit-'+$d+'.svg') 5 7 $body
}
