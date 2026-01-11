Imports System.IO
'========================================
' 03_Exportar_TODO_P
' Imprime los IDW del conjunto y de todas las piezas (si existen)
' y ejecuta la regla "02_Exportar_PDF" dentro de cada IDW.
'========================================

Sub Main()
    Const PRINT_IDW As Boolean = True
    Const EXTERNAL_PDF_RULE As String = "C:\edusonros_projects\SINFINES_CONRAD\iLogic\02_Exportar_PDF.vb"

    Dim outRoot As String = "C:\edusonros_projects\SINFINES_CONRAD\PDF\"
    If Not System.IO.Directory.Exists(outRoot) Then
        System.IO.Directory.CreateDirectory(outRoot)
    End If

    Dim asmDoc As AssemblyDocument = ThisDoc.Document

    ' 1) Imprimir IDW del conjunto (mismo nombre que IAM)
    Dim asmPath As String = asmDoc.FullFileName
    Dim asmFolder As String = System.IO.Path.GetDirectoryName(asmPath)
    Dim asmNameNoExt As String = System.IO.Path.GetFileNameWithoutExtension(asmPath)
    Dim idwAsm As String = System.IO.Path.Combine(asmFolder, asmNameNoExt & ".idw")

    ExportIdwByRunningRule(idwAsm, "02_Exportar_PDF", PRINT_IDW, EXTERNAL_PDF_RULE)

    ' 2) Imprimir IDW de cada pieza si existe
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

        ExportIdwByRunningRule(idwPart, "02_Exportar_PDF", PRINT_IDW, EXTERNAL_PDF_RULE)
    Next

    MessageBox.Show("Impresión finalizada y PDFs en: " & outRoot, "iLogic")
End Sub

Private Sub ExportIdwByRunningRule(idwPath As String, ruleName As String, printIdw As Boolean, externalRulePath As String)
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
        oDoc.Activate()
        iLogicVb.RunRule(oDoc, ruleName)
        oDoc.Update()
        oDoc.Save2(True)

        Dim drawDoc As DrawingDocument = TryCast(oDoc, DrawingDocument)
        If printIdw AndAlso Not drawDoc Is Nothing Then
            Dim pm As PrintManager = drawDoc.PrintManager
            pm.SubmitPrint()
        End If
    Catch ex As Exception
        Dim externalRan As Boolean = False
        If System.IO.File.Exists(externalRulePath) Then
            Try
                oDoc.Activate()
                iLogicVb.RunExternalRule(externalRulePath)
                oDoc.Update()
                oDoc.Save2(True)
                externalRan = True
            Catch
                externalRan = False
            End Try
        End If

        If Not externalRan Then
            MessageBox.Show("No se pudo ejecutar '" & ruleName & "' en " & idwPath & vbCrLf &
                            "Verifica que la regla existe dentro de ese IDW o usa la regla externa." & vbCrLf &
                            ex.Message, "iLogic")
        End If
    Finally
        Try
            oDoc.Close(True)
        Catch
        End Try
    End Try
End Sub
