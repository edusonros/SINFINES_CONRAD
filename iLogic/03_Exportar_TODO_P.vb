'========================================
' 03_Exportar_TODO_P
' Exporta PDF del conjunto y de todas las piezas (si existe su IDW)
' ejecutando la regla "02_Exportar_PDF" dentro de cada IDW.
'========================================

Sub Main()
    Dim outRoot As String = "C:\edusonros_projects\SINFINES_CONRAD\PDF\"
    If Not System.IO.Directory.Exists(outRoot) Then
        System.IO.Directory.CreateDirectory(outRoot)
    End If

    Dim asmDoc As AssemblyDocument = ThisDoc.Document

    ' 1) Exportar IDW del conjunto (mismo nombre que IAM)
    Dim asmPath As String = asmDoc.FullFileName
    Dim asmFolder As String = System.IO.Path.GetDirectoryName(asmPath)
    Dim asmNameNoExt As String = System.IO.Path.GetFileNameWithoutExtension(asmPath)
    Dim idwAsm As String = System.IO.Path.Combine(asmFolder, asmNameNoExt & ".idw")

    ExportIdwByRunningRule(idwAsm, "02_Exportar_PDF")

    ' 2) Exportar IDW de cada pieza si existe
    For Each refDoc As Document In asmDoc.AllReferencedDocuments
        If refDoc.DocumentType <> DocumentTypeEnum.kPartDocumentObject Then
            Continue For
        End If

        Dim pPath As String = refDoc.FullFileName
        If String.IsNullOrWhiteSpace(pPath) Then
            Continue For
        End If

        Dim pFolder As String = System.IO.Path.GetDirectoryName(pPath)
        Dim pName As String = System.IO.Path.GetFileNameWithoutExtension(pPath)
        Dim idwPart As String = System.IO.Path.Combine(pFolder, pName & ".idw")

        ExportIdwByRunningRule(idwPart, "02_Exportar_PDF")
    Next

    MessageBox.Show("Exportación PDF finalizada (conjunto + piezas encontradas).", "iLogic")
End Sub

Private Sub ExportIdwByRunningRule(idwPath As String, ruleName As String)
    If Not System.IO.File.Exists(idwPath) Then
        ' No hay plano para esa pieza → lo saltamos
        Exit Sub
    End If

    Dim oDoc As Document = Nothing
    Try
        oDoc = ThisApplication.Documents.Open(idwPath, True) ' True = Visible
    Catch
        Exit Sub
    End Try

    Try
        ' Ejecuta la regla que vive DENTRO de ese IDW
        iLogicVb.RunRule(ruleName)
        oDoc.Update()
        oDoc.Save2(True)
    Catch
        ' Si no existe la regla en ese IDW, no rompemos
    Finally
        Try
            oDoc.Close(True)
        Catch
        End Try
    End Try
End Sub
