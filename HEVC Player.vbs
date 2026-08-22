Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
args = ""
For Each a In WScript.Arguments
    args = args & " """ & a & """"
Next
py = sh.ExpandEnvironmentStrings("%LocalAppData%\Programs\Python\Python313\pythonw.exe")
sh.CurrentDirectory = base
sh.Run """" & py & """ """ & base & "\hevc_player.py""" & args, 0, False
