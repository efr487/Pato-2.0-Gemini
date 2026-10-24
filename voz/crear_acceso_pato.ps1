$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\pythonw.exe'
$sh = New-Object -ComObject WScript.Shell
$esc = [Environment]::GetFolderPath('Desktop')
$l = $sh.CreateShortcut((Join-Path $esc 'Pato (mostrar).lnk'))
$l.TargetPath = $py
$l.Arguments = '"' + (Join-Path $aqui 'mostrar_pato.pyw') + '"'
$l.WorkingDirectory = $aqui
$l.Description = 'Vuelve a mostrar a Pato'
$l.Save()
Write-Output ('Creado en ' + $esc)
