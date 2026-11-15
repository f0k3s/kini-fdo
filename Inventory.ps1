#requires -Version 5.1
<#
.SYNOPSIS
    Инвентаризация локального ПК под Windows и выгрузка характеристик в CSV.
.EXAMPLE
    .\Inventory.ps1 -Demo
.EXAMPLE
    .\Inventory.ps1
.EXAMPLE
    .\Inventory.ps1 -SelfTest
.EXAMPLE
    .\Inventory.ps1 -Metrics
.NOTES
    По умолчанию отчёт сохраняется в reports рядом со скриптом.
    -Demo создаёт отчёт с четырьмя вымышленными ПК.
#>
[CmdletBinding(DefaultParameterSetName = 'Local')]
param(
    [Parameter(ParameterSetName = 'Local')]
    [Parameter(ParameterSetName = 'Demo')]
    [ValidateNotNullOrEmpty()]
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'reports'),

    [Parameter(Mandatory, ParameterSetName = 'Demo')]
    [switch]$Demo,

    [Parameter(Mandatory, ParameterSetName = 'Tests')]
    [switch]$SelfTest,

    [Parameter(Mandatory, ParameterSetName = 'Metrics')]
    [switch]$Metrics
)

function ConvertTo-InventorySerial {
    param([AllowNull()][string]$Value)

    $serial = ([string]$Value).Trim([char[]]@(0, 9, 10, 13, 32))
    $placeholder = '^(To be filled by O\.E\.M\.?|Default string|System Serial Number|Serial Number|None|Unknown|N/A|Not Specified|Not Available|Not Applicable|0+|F{8,}|[-.]+)$'
    if ([string]::IsNullOrWhiteSpace($serial) -or $serial -match $placeholder) {
        return 'Не указан'
    }
    return $serial
}

function Get-InventoryMediaType {
    param([int]$MediaType)

    if ($MediaType -eq 3) {
        return 'HDD'
    }
    if ($MediaType -eq 4) {
        return 'SSD'
    }
    if ($MediaType -eq 5) {
        return 'SCM'
    }
    return 'Не определён'
}

function Read-InventoryCim {
    param(
        [string]$ClassName,
        [System.Collections.Generic.List[string]]$Warnings,
        [string]$Namespace = 'root/cimv2',
        [string]$Filter
    )

    $query = @{ ClassName = $ClassName; Namespace = $Namespace; ErrorAction = 'Stop' }
    if ($Filter) {
        $query.Filter = $Filter
    }
    try {
        Get-CimInstance @query
    }
    catch {
        $Warnings.Add(('{0}: {1}' -f $ClassName, $_.Exception.Message))
    }
}

function Get-InventoryWindowsData {
    $warnings = [System.Collections.Generic.List[string]]::new()
    $computer = Read-InventoryCim -ClassName Win32_ComputerSystem -Warnings $warnings |
        Select-Object -First 1
    if ($null -eq $computer) {
        throw ('Не удалось прочитать сведения о компьютере. {0}' -f ($warnings -join ' | '))
    }

    $storage = 'root/Microsoft/Windows/Storage'
    $data = [pscustomobject]@{
        Computer = $computer
        Bios = (Read-InventoryCim -ClassName Win32_BIOS -Warnings $warnings | Select-Object -First 1)
        OS = (Read-InventoryCim -ClassName Win32_OperatingSystem -Warnings $warnings | Select-Object -First 1)
        CPU = @(Read-InventoryCim -ClassName Win32_Processor -Warnings $warnings)
        Memory = @(Read-InventoryCim -ClassName Win32_PhysicalMemory -Warnings $warnings)
        Board = (Read-InventoryCim -ClassName Win32_BaseBoard -Warnings $warnings | Select-Object -First 1)
        GPU = @(Read-InventoryCim -ClassName Win32_VideoController -Warnings $warnings)
        Drives = @(Read-InventoryCim -ClassName Win32_DiskDrive -Warnings $warnings)
        StorageDisks = @(Read-InventoryCim -ClassName MSFT_Disk -Warnings $warnings -Namespace $storage)
        MediaDisks = @(Read-InventoryCim -ClassName MSFT_PhysicalDisk -Warnings $warnings -Namespace $storage)
        Network = @(Read-InventoryCim -ClassName Win32_NetworkAdapter -Warnings $warnings -Filter 'PhysicalAdapter = TRUE')
    }
    $data | Add-Member -NotePropertyName Warnings -NotePropertyValue ($warnings.ToArray())
    return $data
}

function Get-InventoryDrives {
    param($Data)

    $busNames = @{
        1 = 'SCSI'; 2 = 'ATAPI'; 3 = 'ATA'; 4 = 'IEEE 1394'; 5 = 'SSA'; 6 = 'Fibre Channel'
        7 = 'USB'; 8 = 'RAID'; 9 = 'iSCSI'; 10 = 'SAS'; 11 = 'SATA'; 12 = 'SD'; 13 = 'MMC'
        14 = 'Virtual'; 15 = 'File Backed Virtual'; 16 = 'Storage Spaces'; 17 = 'NVMe'
        18 = 'SCM'; 19 = 'UFS'
    }

    $drives = foreach ($drive in ($Data.Drives | Sort-Object Index)) {
        $storageDisk = $null
        if ($null -ne $drive.Index) {
            $storageDisk = $Data.StorageDisks | Where-Object Number -EQ $drive.Index | Select-Object -First 1
        }
        $serial = ConvertTo-InventorySerial $drive.SerialNumber
        if ($serial -eq 'Не указан') {
            $serial = ConvertTo-InventorySerial $storageDisk.SerialNumber
        }
        $bus = $busNames[[int]$storageDisk.BusType]
        if (-not $bus) {
            $bus = ([string]$drive.InterfaceType).Trim()
        }
        if (-not $bus) {
            $bus = 'Не определён'
        }
        $size = [uint64]$storageDisk.Size
        if ($size -eq 0) {
            $size = [uint64]$drive.Size
        }
        $sizeText = 'Объём не указан'
        if ($size -gt 0) {
            $sizeText = ('{0} ГиБ' -f [Math]::Round($size / 1GB, 1))
        }
        [pscustomobject]@{
            Index = $drive.Index
            Model = ([string]$drive.Model).Trim()
            Serial = $serial
            Bus = $bus
            SizeText = $sizeText
            Media = 'Не определён'
        }
    }

    # Значение MediaType применяется только при однозначном совпадении серийных номеров.
    foreach ($drive in $drives) {
        if ($drive.Serial -ne 'Не указан') {
            $sameSerial = @($drives | Where-Object Serial -EQ $drive.Serial)
            $mediaMatches = @($Data.MediaDisks | Where-Object {
                (ConvertTo-InventorySerial $_.SerialNumber) -eq $drive.Serial
            })
            if ($sameSerial.Count -eq 1 -and $mediaMatches.Count -eq 1) {
                $drive.Media = Get-InventoryMediaType $mediaMatches[0].MediaType
            }
        }
        $drive
    }
}

function ConvertTo-InventoryCell {
    param([AllowNull()]$Value)

    if ($Value -is [string] -and $Value -match '^(\s*[=+@-]|[\t\r\n])') {
        return "'" + $Value
    }
    return $Value
}

function ConvertTo-InventoryRow {
    param($Data, [string]$Mode, [string]$CollectedAt)

    $diskText = foreach ($disk in (Get-InventoryDrives $Data)) {
        ('#{0} {1} ({2}, {3}, {4}, S/N {5})' -f $disk.Index, $disk.Model,
            $disk.Media, $disk.Bus, $disk.SizeText, $disk.Serial)
    }
    $networkText = foreach ($adapter in ($Data.Network | Where-Object MACAddress | Sort-Object Index)) {
        '{0}: {1}' -f $adapter.Name, ([string]$adapter.MACAddress).Trim().ToUpperInvariant()
    }
    $videoText = ($Data.GPU | ForEach-Object { ([string]$_.Name).Trim() }) -join ' | '
    $driverText = ($Data.GPU | ForEach-Object {
        if ($_.DriverVersion) { '{0}: {1}' -f $_.Name, $_.DriverVersion }
    }) -join ' | '
    $ram = ($Data.Memory | Measure-Object -Property Capacity -Sum).Sum
    if (-not $ram) {
        $ram = $Data.Computer.TotalPhysicalMemory
    }

    $fields = [ordered]@{
        'Режим' = $Mode
        'Дата сбора' = $CollectedAt
        'Имя ПК' = $Data.Computer.Name
        'Производитель ПК' = $Data.Computer.Manufacturer
        'Модель ПК' = $Data.Computer.Model
        'Серийный номер ПК (BIOS)' = (ConvertTo-InventorySerial $Data.Bios.SerialNumber)
        'ОС' = $Data.OS.Caption
        'Версия ОС' = $Data.OS.Version
        'Сборка ОС' = $Data.OS.BuildNumber
        'Процессор' = (($Data.CPU | ForEach-Object { ([string]$_.Name).Trim() }) -join ' | ')
        'Ядра CPU' = ($Data.CPU | Measure-Object -Property NumberOfCores -Sum).Sum
        'Потоки CPU' = ($Data.CPU | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum
        'ОЗУ, ГиБ' = $(if ($ram -gt 0) { [Math]::Round($ram / 1GB, 1) })
        'Производитель платы' = $Data.Board.Manufacturer
        'Модель платы' = $Data.Board.Product
        'Серийный номер платы' = (ConvertTo-InventorySerial $Data.Board.SerialNumber)
        'Версия BIOS' = $Data.Bios.SMBIOSBIOSVersion
        'Видеокарты' = $videoText
        'Драйверы видеокарт' = $driverText
        'Накопители' = ($diskText -join ' | ')
        'Сетевые адаптеры и MAC' = ($networkText -join ' | ')
        'Ошибки сбора' = ($Data.Warnings -join ' | ')
    }
    foreach ($field in @($fields.Keys)) {
        $fields[$field] = ConvertTo-InventoryCell $fields[$field]
    }
    return [pscustomobject]$fields
}

function Export-InventoryCsv {
    param([object[]]$Rows, [string]$Directory, [string]$Name)

    $path = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Directory)
    [void][IO.Directory]::CreateDirectory($path)
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $runId = [guid]::NewGuid().ToString('N')
    $filename = 'Inventory_{0}_{1}_{2}.csv' -f $Name, $stamp, $runId.Substring(0, 8)
    $destination = Join-Path $path $filename
    $temporary = Join-Path $path ('.inventory-{0}.tmp' -f $runId)
    $encoding = 'UTF8'
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        $encoding = 'UTF8BOM'
    }
    try {
        $Rows | Export-Csv -LiteralPath $temporary -Delimiter ';' -Encoding $encoding -NoTypeInformation -ErrorAction Stop
        [IO.File]::Move($temporary, $destination)
    }
    finally {
        if ([IO.File]::Exists($temporary)) {
            [IO.File]::Delete($temporary)
        }
    }
    return $destination
}

function Get-InventoryDemoData {
    $profiles = @(
        'DEMO-PC-01;Dell;OptiPlex 7080;Intel Core i5-10500;6;12;16;Dell;0D4MD1;Intel UHD Graphics 630;Intel I219-LM;Windows 11 Pro;10.0.26100;26100'
        'DEMO-PC-02;Lenovo;ThinkCentre M70q Gen 3;Intel Core i5-12400T;6;12;16;Lenovo;3733;Intel UHD Graphics 730;Intel I219-V;Windows 11 Pro;10.0.26100;26100'
        'DEMO-PC-03;HP;ProDesk 600 G5;Intel Core i5-9500;6;6;8;HP;8591;Intel UHD Graphics 630;Intel I219-LM;Windows 10 Pro;10.0.19045;19045'
        'DEMO-PC-04;Сборный ПК;Рабочая станция;AMD Ryzen 7 5700X;8;16;32;ASUSTeK;PRIME B550M-A;NVIDIA GeForce RTX 3060;Realtek PCIe GbE;Windows 11 Pro;10.0.26100;26100'
    ) | ConvertFrom-Csv -Delimiter ';' -Header Name, Brand, Model, CPU, Cores, Threads, RAM, BoardBrand,
        BoardModel, GPU, Ethernet, OS, Version, Build
    $diskProfiles = @(
        'DEMO-PC-01;0;Samsung SSD 870 EVO 500GB;500107862016;11;4;ATA;DEMO-SSD-010'
        'DEMO-PC-01;1;WDC WD10EZEX 1TB;1000204886016;11;3;ATA;DEMO-HDD-011'
        'DEMO-PC-02;0;WD Blue SN570 500GB;500107862016;17;4;SCSI;DEMO-SSD-020'
        'DEMO-PC-03;0;ST1000DM010 1TB;1000204886016;11;3;ATA;DEMO-HDD-030'
        'DEMO-PC-04;0;Samsung SSD 980 1TB;1000204886016;17;4;SCSI;DEMO-SSD-040'
        'DEMO-PC-04;1;USB External Drive 500GB;500107862016;7;0;USB;'
    ) | ConvertFrom-Csv -Delimiter ';' -Header Host, Number, Model, Size, Bus, Media, Interface, Serial

    for ($i = 0; $i -lt $profiles.Count; $i++) {
        $pc = $profiles[$i]
        $tag = '{0:00}' -f ($i + 1)
        $disks = @($diskProfiles | Where-Object Host -EQ $pc.Name)
        $profileNetwork = @([pscustomobject]@{
            Index = 0; Name = $pc.Ethernet; MACAddress = ('02:00:00:00:{0}:01' -f $tag)
        })
        if ($pc.Name -eq 'DEMO-PC-02') {
            $profileNetwork += [pscustomobject]@{ Index = 1; Name = 'Intel Wi-Fi 6 AX201'; MACAddress = '02:00:00:00:02:02' }
        }
        [pscustomobject]@{
            Computer = [pscustomobject]@{ Name = $pc.Name; Manufacturer = $pc.Brand; Model = $pc.Model }
            Bios = [pscustomobject]@{ SerialNumber = "DEMO-PC-SN-$tag"; SMBIOSBIOSVersion = "DEMO-BIOS-$tag" }
            OS = [pscustomobject]@{ Caption = $pc.OS; Version = $pc.Version; BuildNumber = $pc.Build }
            CPU = @([pscustomobject]@{ Name = $pc.CPU; NumberOfCores = [int]$pc.Cores; NumberOfLogicalProcessors = [int]$pc.Threads })
            Memory = @([pscustomobject]@{ Capacity = ([uint64]$pc.RAM * 1GB) })
            Board = [pscustomobject]@{ Manufacturer = $pc.BoardBrand; Product = $pc.BoardModel; SerialNumber = "DEMO-MB-$tag" }
            GPU = @([pscustomobject]@{ Name = $pc.GPU; DriverVersion = 'Демо' })
            Drives = @($disks | ForEach-Object {
                [pscustomobject]@{ Index = [int]$_.Number; Model = $_.Model; Size = [uint64]$_.Size; InterfaceType = $_.Interface; SerialNumber = $_.Serial }
            })
            StorageDisks = @($disks | ForEach-Object {
                [pscustomobject]@{ Number = [int]$_.Number; BusType = [int]$_.Bus; Size = [uint64]$_.Size; SerialNumber = $_.Serial }
            })
            MediaDisks = @($disks | ForEach-Object {
                [pscustomobject]@{ MediaType = [int]$_.Media; SerialNumber = $_.Serial }
            })
            Network = $profileNetwork
            Warnings = @()
        }
    }
}

# Учебные проверки функций, которые обрабатывают и сохраняют отчёт.
function Invoke-InventorySelfTest {
    $ErrorActionPreference = 'Stop'

    function Assert-Equal {
        param($Expected, $Actual)

        if ($Expected -cne $Actual) {
            throw ('Ожидалось «{0}», получено «{1}».' -f $Expected, $Actual)
        }
    }

    function Assert-Contains {
        param([string]$Text, [string]$Part)

        if (-not $Text.Contains($Part)) {
            throw ('В строке отсутствует «{0}».' -f $Part)
        }
    }

    $results = [System.Collections.Generic.List[object]]::new()
    function Test-Case {
        param([string]$Name, [scriptblock]$Body)

        try {
            & $Body
            $results.Add($true)
            Write-Host "[PASS] $Name"
        }
        catch {
            $results.Add($false)
            Write-Host ('[FAIL] {0}. {1}' -f $Name, $_.Exception.Message)
        }
    }

    Test-Case 'U01 Серийный номер очищается от пробелов' {
        Assert-Equal 'ABC123' (ConvertTo-InventorySerial ' ABC123 ')
    }
    Test-Case 'U02 Пустой и шаблонный серийные номера' {
        foreach ($value in @($null, '', '  ', 'To Be Filled By O.E.M.', '0000', 'Default string')) {
            Assert-Equal 'Не указан' (ConvertTo-InventorySerial $value)
        }
    }
    Test-Case 'U03 HDD, SSD, SCM и неизвестный тип' {
        Assert-Equal 'HDD' (Get-InventoryMediaType 3)
        Assert-Equal 'SSD' (Get-InventoryMediaType 4)
        Assert-Equal 'SCM' (Get-InventoryMediaType 5)
        Assert-Equal 'Не определён' (Get-InventoryMediaType 0)
        Assert-Equal 'Не определён' (Get-InventoryMediaType 99)
    }
    Test-Case 'U04 SATA SSD и HDD на одном ПК' {
        $data = @(Get-InventoryDemoData)[0]
        $disks = @(Get-InventoryDrives $data)
        Assert-Equal 2 $disks.Count
        Assert-Equal 'SSD' $disks[0].Media
        Assert-Equal 'SATA' $disks[0].Bus
        Assert-Equal 'HDD' $disks[1].Media
    }
    Test-Case 'U05 NVMe SSD и два MAC-адреса' {
        $data = @(Get-InventoryDemoData)[1]
        $row = ConvertTo-InventoryRow $data 'Проверка' 'Учебный тест'
        Assert-Contains $row.Накопители '(SSD, NVMe,'
        Assert-Contains $row.'Сетевые адаптеры и MAC' '02:00:00:00:02:01'
        Assert-Contains $row.'Сетевые адаптеры и MAC' '02:00:00:00:02:02'
    }
    Test-Case 'U06 USB без серийного номера' {
        $data = @(Get-InventoryDemoData)[3]
        $disk = @(Get-InventoryDrives $data)[1]
        Assert-Equal 'USB' $disk.Bus
        Assert-Equal 'Не указан' $disk.Serial
        Assert-Equal 'Не определён' $disk.Media
    }
    Test-Case 'U07 Неоднозначное сопоставление дисков' {
        $data = @(Get-InventoryDemoData)[0]
        $data.MediaDisks += [pscustomobject]@{ SerialNumber = $data.Drives[0].SerialNumber; MediaType = 3 }
        $disk = @(Get-InventoryDrives $data)[0]
        Assert-Equal 'Не определён' $disk.Media
    }
    Test-Case 'U08 Резервный источник данных о диске' {
        $data = @(Get-InventoryDemoData)[0]
        $data.StorageDisks = @()
        $data.MediaDisks = @()
        $disk = @(Get-InventoryDrives $data)[0]
        Assert-Equal 'ATA' $disk.Bus
        Assert-Equal 'Не определён' $disk.Media
        Assert-Contains $disk.SizeText 'ГиБ'
    }
    Test-Case 'U09 Обработка формул в полях CSV' {
        Assert-Equal "'=1+2" (ConvertTo-InventoryCell '=1+2')
        Assert-Equal "'  +sum" (ConvertTo-InventoryCell '  +sum')
        Assert-Equal 'DEMO-01' (ConvertTo-InventoryCell 'DEMO-01')
        Assert-Equal 16 (ConvertTo-InventoryCell 16)
    }
    Test-Case 'U10 Поиск типа диска по запасному серийному номеру' {
        $data = @(Get-InventoryDemoData)[0]
        $data.Drives[0].SerialNumber = $null
        $disk = @(Get-InventoryDrives $data)[0]
        Assert-Equal 'DEMO-SSD-010' $disk.Serial
        Assert-Equal 'SSD' $disk.Media
    }
    Test-Case 'U11 Частичные данные CIM попадают в отчёт' {
        $data = @(Get-InventoryDemoData)[0]
        $data.Board = $null
        $data.GPU = @()
        $data.Memory = @()
        $data.Computer | Add-Member -NotePropertyName TotalPhysicalMemory -NotePropertyValue (16GB)
        $data.Warnings = @('Win32_BaseBoard: тестовая ошибка')
        $row = ConvertTo-InventoryRow $data 'Проверка' 'Учебный тест'
        Assert-Equal 'Не указан' $row.'Серийный номер платы'
        Assert-Equal 16 $row.'ОЗУ, ГиБ'
        Assert-Contains $row.'Ошибки сбора' 'Win32_BaseBoard'
    }
    Test-Case 'U12 Повторный экспорт создаёт самостоятельные файлы' {
        $temp = Join-Path ([IO.Path]::GetTempPath()) ('inventory-unit-' + [guid]::NewGuid().ToString('N'))
        try {
            $row = ConvertTo-InventoryRow @(Get-InventoryDemoData)[0] 'Проверка' 'Учебный тест'
            $first = Export-InventoryCsv -Rows @($row) -Directory $temp -Name 'UNIT'
            $second = Export-InventoryCsv -Rows @($row) -Directory $temp -Name 'UNIT'
            Assert-Equal $false ($first -eq $second)
            $bytes = [IO.File]::ReadAllBytes($first)
            Assert-Equal 'EF-BB-BF' ([BitConverter]::ToString($bytes, 0, 3))
            Assert-Equal 'DEMO-PC-01' (Import-Csv -LiteralPath $second -Delimiter ';').'Имя ПК'
            Assert-Equal 2 @(Get-ChildItem -LiteralPath $temp -Force).Count
        }
        finally {
            if (Test-Path -LiteralPath $temp) {
                Remove-Item -LiteralPath $temp -Recurse -Force
            }
        }
    }

    $passed = @($results | Where-Object { $_ }).Count
    $failed = $results.Count - $passed
    Write-Host ('Итого: успешно {0}, ошибок {1}.' -f $passed, $failed)
    if ($failed -gt 0) { throw 'Есть непрошедшие тесты.' }
}

# Подсчёт метрик по токенам собственного исходного файла.
function Show-InventoryMetrics {
    param([string]$Path)

    $tokens = $null
    $parseErrors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count -gt 0) { throw ($parseErrors -join [Environment]::NewLine) }
    $function = $ast.Find({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-InventoryMediaType'
    }, $false)
    if ($null -eq $function) { throw 'Функция Get-InventoryMediaType отсутствует.' }

    function Measure-Halstead {
        param([object[]]$Tokens)

        $operatorKinds = @(
            'LParen', 'LBracket', 'LCurly', 'AtParen', 'AtCurly', 'DollarParen', 'Comma', 'Semi',
            'Dot', 'ColonColon'
        )
        $ignoredKinds = @('RParen', 'RBracket', 'RCurly', 'NewLine', 'Comment', 'EndOfInput')
        $flags = [System.Management.Automation.Language.TokenFlags]
        $operatorFlags = $flags::Keyword -bor $flags::CommandName -bor $flags::BinaryOperator -bor
            $flags::UnaryOperator -bor $flags::AssignmentOperator
        $operators = @()
        $operands = @()

        foreach ($token in $Tokens) {
            if ($token.Kind -in $ignoredKinds) { continue }
            $pairedSeparator = switch ($token.Kind) {
                LParen { '()' }
                LBracket { '[]' }
                LCurly { '{}' }
                AtParen { '@()' }
                AtCurly { '@{}' }
                DollarParen { '$()' }
            }
            if ($pairedSeparator) {
                $operators += $pairedSeparator
            }
            elseif ($token.Kind -in $operatorKinds -or ($token.TokenFlags -band $operatorFlags)) {
                $operators += $token.Text
            }
            else {
                $operands += $token.Text
            }
        }

        $operatorGroups = @($operators | Group-Object -CaseSensitive)
        $operandGroups = @($operands | Group-Object -CaseSensitive)
        $n = $operatorGroups.Count + $operandGroups.Count
        $length = $operators.Count + $operands.Count
        $volume = $length * [Math]::Log($n, 2)
        $difficulty = ($operatorGroups.Count / 2) * ($operands.Count / $operandGroups.Count)
        [pscustomobject]@{
            OperatorGroups = $operatorGroups
            OperandGroups = $operandGroups
            N1 = $operators.Count
            N2 = $operands.Count
            Vocabulary = $n
            Length = $length
            Volume = $volume
            Difficulty = $difficulty
            Effort = $volume * $difficulty
        }
    }

    function Show-Halstead {
        param($Metrics)

        $format = [Globalization.CultureInfo]::InvariantCulture
        Write-Host ('n1={0}, n2={1}, N1={2}, N2={3}' -f $Metrics.OperatorGroups.Count,
            $Metrics.OperandGroups.Count, $Metrics.N1, $Metrics.N2)
        Write-Host ('Словарь n = {0}, длина N = {1}' -f $Metrics.Vocabulary, $Metrics.Length)
        Write-Host ('V = {0}, D = {1}, E = {2}' -f $Metrics.Volume.ToString('F2', $format),
            $Metrics.Difficulty.ToString('F3', $format), $Metrics.Effort.ToString('F2', $format))
    }

    $start = $function.Body.ParamBlock.Extent.EndOffset
    $end = $function.Body.EndBlock.Extent.EndOffset
    $functionTokens = @($tokens | Where-Object { $_.Extent.StartOffset -ge $start -and $_.Extent.EndOffset -le $end })
    $decisions = @($functionTokens | Where-Object Kind -EQ 'If').Count
    $functionMetrics = Measure-Halstead $functionTokens
    $scriptMetrics = Measure-Halstead $tokens

    Write-Host 'Get-InventoryMediaType | исполняемое тело без param'
    Write-Host ('Операторы: ' + (($functionMetrics.OperatorGroups | ForEach-Object { '{0} × {1}' -f $_.Name, $_.Count }) -join ', '))
    Write-Host ('Операнды:  ' + (($functionMetrics.OperandGroups | ForEach-Object { '{0} × {1}' -f $_.Name, $_.Count }) -join ', '))
    Write-Host ('McCabe M = {0} (1 + {1} проверки)' -f ($decisions + 1), $decisions)
    Show-Halstead $functionMetrics
    Write-Host ''
    Write-Host 'Inventory.ps1 | полный основной файл'
    Show-Halstead $scriptMetrics
}

if ($MyInvocation.InvocationName -eq '.') {
    return
}

if ($SelfTest) {
    Invoke-InventorySelfTest
    return
}
if ($Metrics) {
    Show-InventoryMetrics -Path $PSCommandPath
    return
}

$collectedAt = [DateTimeOffset]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz', [Globalization.CultureInfo]::InvariantCulture)
if ($Demo) {
    $mode = 'Демонстрация'
    $prefix = 'DEMO'
    $records = @(Get-InventoryDemoData)
}
else {
    if ($env:OS -ne 'Windows_NT') {
        throw 'Обычный режим доступен в Windows. Для учебного запуска используй -Demo.'
    }
    $mode = 'Локальный сбор Windows'
    $records = @(Get-InventoryWindowsData)
    $prefix = $records[0].Computer.Name -replace '[^\p{L}\p{Nd}_.-]', '_'
    if (-not $prefix) {
        $prefix = 'PC'
    }
}

$rows = @($records | ForEach-Object { ConvertTo-InventoryRow $_ $mode $collectedAt })
try {
    $report = Export-InventoryCsv -Rows $rows -Directory $OutputDirectory -Name $prefix
}
catch {
    throw ('Не удалось сохранить CSV в папке «{0}». {1}' -f $OutputDirectory, $_.Exception.Message)
}

Write-Host ('Режим: {0}' -f $mode)
Write-Host ('ПК: {0}' -f ($rows.'Имя ПК' -join ', '))
Write-Host ('Строк в отчёте: {0}' -f $rows.Count)
$records | ForEach-Object { $_.Warnings } | ForEach-Object { Write-Warning $_ }
Write-Host ('Файл CSV: {0}' -f $report)
