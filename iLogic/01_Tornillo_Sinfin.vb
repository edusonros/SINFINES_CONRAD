AddReference "System.Web.Extensions"

'========================================
' 01_Tornillo_Sinfin
' Lee JSON y aplica parámetros SOLO a IPTs
'========================================

Sub Main()
    Dim jsonPath As String = "C:\edusonros_projects\SINFINES_CONRAD\iLogic\Tornillo Sinfin_v001.json"
    If Not System.IO.File.Exists(jsonPath) Then
        MessageBox.Show("No existe el JSON: " & jsonPath, "iLogic")
        Exit Sub
    End If

    Dim txt As String = System.IO.File.ReadAllText(jsonPath)
    Dim ser As New System.Web.Script.Serialization.JavaScriptSerializer()
    Dim root = ser.DeserializeObject(txt)

    Dim globals As Object = Nothing
    Try
        globals = DirectCast(root, Dictionary(Of String, Object))("global")
    Catch
        MessageBox.Show("JSON sin nodo 'global'.", "iLogic")
        Exit Sub
    End Try

    Dim dict = DirectCast(globals, Dictionary(Of String, Object))

    Dim oAsm As AssemblyDocument = ThisDoc.Document
    For Each refDoc As Document In oAsm.AllReferencedDocuments
        If refDoc.DocumentType <> DocumentTypeEnum.kPartDocumentObject Then
            Continue For
        End If

        ApplyDictToDocParams(refDoc, dict)

        Try
            refDoc.Update()
            refDoc.Save2(True)
        Catch
            ' Silencio: si está read-only o no procede
        End Try
    Next

    ' Actualizar ensamblaje al final
    Try
        ThisDoc.Document.Update()
        ThisDoc.Document.Save2(True)
    Catch
    End Try

    ' Exportar PDFs (conjunto + piezas)
    Try
        iLogicVb.RunRule("03_Exportar_TODO_P")
    Catch
    End Try

    MessageBox.Show("Parámetros aplicados a IPTs y documentos actualizados.", "iLogic")
End Sub

Private Sub ApplyDictToDocParams(doc As Document, dict As Dictionary(Of String, Object))
    Dim params As Parameters = Nothing
    Try
        params = DirectCast(doc, PartDocument).ComponentDefinition.Parameters
    Catch
        Exit Sub
    End Try

    For Each kvp In dict
        Dim pName As String = kvp.Key
        Dim pValObj As Object = kvp.Value

        Dim v As Double
        Try
            v = CDbl(pValObj)
        Catch
            Continue For
        End Try

        Dim p As Parameter = Nothing
        Try
            p = params.UserParameters.Item(pName)
        Catch
            Try
                p = params.Item(pName)
            Catch
                p = Nothing
            End Try
        End Try

        If p Is Nothing Then Continue For

        Try
            If p.Units = "mm" Or p.Units = "cm" Or p.Units = "m" Then
                p.Expression = v.ToString(System.Globalization.CultureInfo.InvariantCulture) & " mm"
            ElseIf p.Units = "deg" Then
                p.Expression = v.ToString(System.Globalization.CultureInfo.InvariantCulture) & " deg"
            Else
                p.Expression = v.ToString(System.Globalization.CultureInfo.InvariantCulture)
            End If
        Catch
            ' Si está bloqueado por fórmula, ignora
        End Try
    Next
End Sub
