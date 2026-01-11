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
    Dim dict = ParseGlobalParams(txt)
    If dict Is Nothing OrElse dict.Count = 0 Then
        MessageBox.Show("JSON sin nodo 'global' o sin parámetros.", "iLogic")
        Exit Sub
    End If
    ShowParamsSummary(dict, jsonPath)

    Dim oAsm As AssemblyDocument = ThisDoc.Document
    For Each refDoc As Document In oAsm.AllReferencedDocuments
        If refDoc.DocumentType <> DocumentTypeEnum.kPartDocumentObject Then
            Continue For
        End If

        Dim partPath As String = refDoc.FullFileName
        Dim partDoc As Document = refDoc
        Dim openedPart As Boolean = False

        Try
            If Not String.IsNullOrWhiteSpace(partPath) Then
                partDoc = ThisApplication.Documents.Open(partPath, True)
                openedPart = True
            End If
        Catch
            partDoc = refDoc
        End Try

        Try
            ApplyDictToDocParams(partDoc, dict)
            MessageBox.Show("Actualizando IPT: " & partDoc.FullFileName, "iLogic")
            partDoc.Update()
            partDoc.Save2(True)
        Catch
            ' Silencio: si está read-only o no procede
        Finally
            If openedPart Then
                Try
                    partDoc.Close(True)
                Catch
                End Try
            End If
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
        MessageBox.Show("Iniciando exportación de PDFs (IDW)...", "iLogic")
        iLogicVb.RunRule("03_Exportar_TODO_P")
    Catch
    End Try

    MessageBox.Show("Parámetros aplicados a IPTs y documentos actualizados.", "iLogic")
End Sub

Private Sub ShowParamsSummary(dict As Dictionary(Of String, Object), jsonPath As String)
    Dim sb As New System.Text.StringBuilder()
    sb.AppendLine("JSON leído: " & jsonPath)
    sb.AppendLine("Parámetros detectados:")
    For Each kvp In dict
        sb.AppendLine(" - " & kvp.Key & " = " & CStr(kvp.Value))
    Next
    MessageBox.Show(sb.ToString(), "Parámetros JSON")
End Sub

Private Function ParseGlobalParams(jsonText As String) As Dictionary(Of String, Object)
    Dim globalMatch As System.Text.RegularExpressions.Match =
        System.Text.RegularExpressions.Regex.Match(
            jsonText,
            """global""\s*:\s*\{(?<body>.*?)\}",
            System.Text.RegularExpressions.RegexOptions.Singleline
        )

    If Not globalMatch.Success Then
        Return Nothing
    End If

    Dim body As String = globalMatch.Groups("body").Value
    Dim dict As New Dictionary(Of String, Object)(StringComparer.OrdinalIgnoreCase)
    Dim pairRegex As New System.Text.RegularExpressions.Regex(
        """(?<key>[^""]+)""\s*:\s*(?:""(?<str>[^""]*)""|(?<num>-?\d+(?:[.,]\d+)?))"
    )

    For Each m As System.Text.RegularExpressions.Match In pairRegex.Matches(body)
        Dim key As String = m.Groups("key").Value
        If m.Groups("str").Success Then
            dict(key) = m.Groups("str").Value
        Else
            Dim numText As String = m.Groups("num").Value.Replace(",", ".")
            Dim val As Double
            If Double.TryParse(
                numText,
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture,
                val
            ) Then
                dict(key) = val
            Else
                dict(key) = numText
            End If
        End If
    Next

    Return dict
End Function

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
