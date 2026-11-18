Подпись MKV Muxer (Authenticode)
================================

Текущие артефакты НЕ подписаны. Это означает:
- Windows SmartScreen показывает «Неизвестный издатель»;
- в свойствах файла нет вкладки «Цифровые подписи»;
- антивирус может относиться к файлу подозрительнее.

Подпись не делает программу «безопасной» автоматически, но подтверждает
издателя и позволяет SmartScreen накопить репутацию.


1. Какой нужен сертификат
-------------------------
Нужен Code Signing Certificate (Authenticode), не TLS/SSL.

Типы:
- OV (Organization Validation) — дешевле, репутация SmartScreen набирается
  по мере загрузок. Ориентировочно 200–400 USD/год.
- EV (Extended Validation) — дороже (ориентировочно 300–600 USD/год),
  но репутация SmartScreen появляется значительно быстрее.

Важно: с июня 2023 года закрытые ключи OV/EV-сертификатов должны храниться
в FIPS 140-2 Level 2 (или выше) оборудовании: USB-токен либо облачный HSM.
Обычный .pfx-файл новые сертификаты не выдают.

Варианты для небольшого/open-source проекта:
- Certum Code Signing (в т.ч. Open Source) — облачная подпись SimplySign;
- SSL.com / Sectigo / DigiCert — OV/EV, токен или облако;
- Microsoft Azure Trusted Signing — самый дешёвый вариант (~10 USD/мес),
  но есть требования к организации и её истории; интеграция через
  Azure.CodeSigning.Dlib.dll;
- SignPath.io — бесплатная подпись для open-source проектов.

Для личного использования и раздачи «друзьям» подпись не обязательна.


2. Инструмент
-------------
signtool.exe входит в Windows SDK (Signing Tools). Проверка:

  signtool /?

Если signtool нет — установите Windows SDK (только компонент
"Windows SDK Signing Tools for Desktop Apps").


3. Порядок подписи для этого проекта
------------------------------------
Подписывать нужно ДО упаковки в ZIP и ДО финального расчёта SHA256.

3.1. Подписать приложение (onedir, его кладёт установщик):

  signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 ^
    /d "MKV Muxer" "dist\MKV_Muxer\MKV_Muxer.exe"

3.2. Подписать portable-версию (onefile):

  signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 ^
    /d "MKV Muxer" "dist\MKV_Muxer.exe"

3.3. Собрать установщик (он запакует уже подписанный onedir):

  "%LOCALAPPDATA%\Programs\InnoSetup7\ISCC.exe" installer\MKV_Muxer.iss

3.4. Подписать установщик:

  signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 ^
    /d "MKV Muxer Setup" "release\MKV_Muxer_1.0_setup.exe"

3.5. Заново собрать portable ZIP (чтобы внутри был подписанный EXE)
     и пересчитать SHA256SUMS.txt.

Выбор сертификата:
- /a — автоматически выбрать подходящий;
- /sha1 <отпечаток> — конкретный сертификат (для токена/хранилища);
- /f cert.pfx /p <пароль> — только если у вас есть pfx (старые сертификаты).

Параметры /tr и /td обязательны: без метки времени подпись станет
недействительной после истечения срока сертификата.


4. Подпись в Inno Setup
-----------------------
1. Tools -> Configure Sign Tools -> Add:
   Name:  signtool
   Command:
   "C:\Program Files (x86)\Windows Kits\10\bin\10.0.XXXXX.0\x64\signtool.exe" sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $f
   ($f — подставляемый файл, $q — кавычка)
2. В installer\MKV_Muxer.iss раскомментировать:
   SignTool=signtool
   SignedUninstaller=yes
3. Пересобрать установщик.

SignedUninstaller=yes подписывает и unins000.exe, который создаёт Inno.


5. Проверка подписи
-------------------
  signtool verify /pa /v "release\MKV_Muxer_1.0_setup.exe"

PowerShell:

  Get-AuthenticodeSignature -LiteralPath "release\MKV_Muxer_1.0_setup.exe" |
    Format-List Status, StatusMessage, SignerCertificate

Ожидаемо: Status = Valid, в SignerCertificate — ваш издатель.

Проверять нужно на чистой машине: подпись, выданная Let's Encrypt-подобным
способом, доверяется только если корневой сертификат CA есть в системе.


6. SmartScreen и антивирус
--------------------------
- Неподписанный файл: «Windows protected your PC» / «Неизвестный издатель».
- OV-подпись: предупреждение может оставаться, пока не накопится репутация
  (зависит от количества загрузок и возраста сертификата).
- EV-подпись: репутация появляется быстро, часто сразу.
- Подпись не гарантирует отсутствие ложных срабатываний антивирусов.
  При ложном срабатывании отправьте файл в Microsoft:
  https://www.microsoft.com/en-us/wdsi/filesubmission
- ZIP-архив нельзя подписать Authenticode. Для архива используйте
  SHA256SUMS.txt (уже есть) или GPG-подпись.


7. Самоподписанный сертификат (только для тестов)
-------------------------------------------------
Для проверки механизма можно создать самоподписанный сертификат:

  New-SelfSignedCertificate -Type CodeSigningCert `
    -Subject "CN=MKV Muxer Test" `
    -CertStoreLocation Cert:\CurrentUser\My

Подписать им файл и добавить сертификат в «Доверенные издатели» на тестовой
машине. На чужих компьютерах такой файл всё равно будет «Неизвестным
издателем» — для публичной раздачи нужен сертификат публичного CA.
