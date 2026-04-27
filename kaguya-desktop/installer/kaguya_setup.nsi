!define APPNAME "Kaguya IDE"
!define APPVERSION "3.1.1"
!define APPNAMEANDVERSION "${APPNAME} ${APPVERSION}"
!define APPEXE "KaguyaIDE.exe"
!define APPICON "kaguya.ico"
!define COMPANYNAME "Kaguya"

Name "${APPNAMEANDVERSION}"
Icon "${APPICON}"
OutFile "KaguyaIDE-${APPVERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\${APPNAME}"
InstallDirRegKey HKLM "Software\${COMPANYNAME}\${APPNAME}" "InstallDir"
RequestExecutionLevel admin

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!define MUI_ICON "${APPICON}"
!define MUI_UNICON "${APPICON}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN "$INSTDIR\${APPEXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APPNAME}"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

LangString SEC01_NAME ${LANG_ENGLISH} "Main Application"
LangString SEC01_NAME ${LANG_SIMPCHINESE} "主程序"
LangString SEC02_NAME ${LANG_ENGLISH} "Register .kaguya File Association"
LangString SEC02_NAME ${LANG_SIMPCHINESE} "注册 .kaguya 文件关联"
LangString SEC03_NAME ${LANG_ENGLISH} "Security Framework Module"
LangString SEC03_NAME ${LANG_SIMPCHINESE} "安全框架模块"
LangString DESKTOP_SC_NAME ${LANG_ENGLISH} "Kaguya IDE"
LangString DESKTOP_SC_NAME ${LANG_SIMPCHINESE} "辉夜IDE"

Section "$(SEC01_NAME)" SEC01
    SetOutPath "$INSTDIR"
    SetOverwrite on

    File /r "..\dist\KaguyaIDE\*.*"

    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${APPEXE}" "" "$INSTDIR\${APPICON}"
    CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk" "$INSTDIR\uninstall.exe"
    CreateShortCut "$DESKTOP\$(DESKTOP_SC_NAME).lnk" "$INSTDIR\${APPEXE}" "" "$INSTDIR\${APPICON}"

    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "EstimatedSize" "$0"
SectionEnd

Section "$(SEC02_NAME)" SEC02
    WriteRegStr HKCR ".kaguya" "" "KaguyaIDE.Project"
    WriteRegStr HKCR "KaguyaIDE.Project" "" "${APPNAME} Project"
    WriteRegStr HKCR "KaguyaIDE.Project\DefaultIcon" "" "$INSTDIR\${APPICON}"
    WriteRegStr HKCR "KaguyaIDE.Project\shell\open\command" "" '"$INSTDIR\${APPEXE}" "%1"'
SectionEnd

Section "$(SEC03_NAME)" SEC03
    SetOutPath "$INSTDIR"
    SetOverwrite on

    File "..\..\kaguya_security_framework.py"
    File "..\..\kaguya_permissions.py"
    File "..\..\kaguya_hooks.py"
    File "..\..\kaguya_tool_system.py"
    File "..\..\kaguya_file_operations.py"
    File "..\..\kaguya_thinking.py"
    File "..\..\kaguya_memory.py"
    File "..\..\ollama_adapter.py"
SectionEnd

Section -Post
    WriteRegStr HKLM "Software\${COMPANYNAME}\${APPNAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\${COMPANYNAME}\${APPNAME}" "Version" "${APPVERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAMEANDVERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayIcon" '"$INSTDIR\${APPICON}"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${APPVERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLInfoAbout" "https://github.com/kaguya-ide"
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section Uninstall
    RMDir /r "$INSTDIR"

    Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
    Delete "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\${APPNAME}"
    Delete "$DESKTOP\Kaguya IDE.lnk"
    Delete "$DESKTOP\辉夜IDE.lnk"

    DeleteRegKey HKLM "Software\${COMPANYNAME}\${APPNAME}"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
    DeleteRegKey HKCR ".kaguya"
    DeleteRegKey HKCR "KaguyaIDE.Project"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "$(SEC01_NAME)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "$(SEC02_NAME)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "$(SEC03_NAME)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END
