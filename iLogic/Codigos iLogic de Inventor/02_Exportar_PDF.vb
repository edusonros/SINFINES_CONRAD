'========================================
' 02_Exportar_PDF
' Exporta el plano activo a PDF (robusto)
'========================================

Sub Main()
    Try
        Dim oDoc As Inventor.DrawingDocument = TryCast(ThisApplication.ActiveDocument, Inventor.DrawingDocument)
        If oDoc Is Nothing Then
            MessageBox.Show("El documento activo no es un plano (IDW).", "iLogic PDF")
            Exit Sub
        End If

        '--- Carpeta destino
        Dim outFolder As String = "C:\edusonros_projects\SINFINES_CONRAD\PDF\"
        If Not System.IO.Directory.Exists(outFolder) Then
            System.IO.Directory.CreateDirectory(outFolder)
        End If

        '--- Referenciado principal (mejor desde la primera vista del Sheet1 si existe)
        Dim refDoc As Inventor.Document = Nothing
        Try
            Dim oSheet As Inventor.Sheet = oDoc.Sheets.Item(1)
            If oSheet.DrawingViews.Count > 0 Then
                refDoc = oSheet.DrawingViews.Item(1).ReferencedDocumentDescriptor.ReferencedDocument
            End If
        Catch
            ' fallback
        End Try

        If refDoc Is Nothing Then
            ' fallback: primer documento referenciado
            refDoc = oDoc.ReferencedDocuments.Item(1)
        End If

        '--- Construir nombre PDF
        Dim baseName As String = System.IO.Path.GetFileNameWithoutExtension(oDoc.FullFileName)

        ' Intenta leer parámetros habituales
        Dim L As Double, DE As Double, DI As Double, E As Double, P As Double, N As Double
        Dim hasL As Boolean = TryGetParamMM(refDoc, "Largo", L)
        Dim hasDE As Boolean = TryGetParamMM(refDoc, "DiametroExterior", DE)
        Dim hasDI As Boolean = TryGetParamMM(refDoc, "DiametroInterior", DI)
        Dim hasE As Boolean = TryGetParamMM(refDoc, "Espesor", E)
        Dim hasP As Boolean = TryGetParamMM(refDoc, "Paso_Espira_01", P) OrElse TryGetParamMM(refDoc, "Paso_Espira", P) OrElse TryGetParamMM(refDoc, "Paso_Esp", P)
        Dim hasN As Boolean = TryGetParamUnitless(refDoc, "Num_Espiras", N) OrElse TryGetParamUnitless(refDoc, "Num_Vueltas", N)

        Dim pdfName As String = baseName & ".pdf"

        ' Si hay datos, los metemos en el nombre
        If hasL Or hasDE Or hasE Or hasP Or hasN Then
            Dim parts As New List(Of String)

            If hasDE Then parts.Add("DE" & CInt(Math.Round(DE)))
            If hasDI Then parts.Add("DI" & CInt(Math.Round(DI)))
            If hasE Then parts.Add("E" & CInt(Math.Round(E)))
            If hasL Then parts.Add("L" & CInt(Math.Round(L)))
            If hasP Then parts.Add("P" & CInt(Math.Round(P)))
            If hasN Then parts.Add("N" & CInt(Math.Round(N)))

            pdfName = baseName & "_" & String.Join("_", parts.ToArray()) & ".pdf"
        End If

        Dim pdfPath As String = System.IO.Path.Combine(outFolder, pdfName)

        If System.IO.File.Exists(pdfPath) Then
            Dim ts As String = DateTime.Now.ToString("yyyyMMdd_HHmmss")
            pdfPath = System.IO.Path.Combine(outFolder, System.IO.Path.GetFileNameWithoutExtension(pdfName) & "_" & ts & ".pdf")
        End If

        '--- Actualizar antes de exportar
        oDoc.Update()

        '--- Traductor PDF
        Dim oPDFAddIn As Inventor.ApplicationAddIn =
            ThisApplication.ApplicationAddIns.ItemById("{0AC6FD96-2F4D-42CE-8BE0-8AEA580399E4}")

        Dim oContext As Inventor.TranslationContext =
            ThisApplication.TransientObjects.CreateTranslationContext()
        oContext.Type = Inventor.IOMechanismEnum.kFileBrowseIOMechanism

        Dim oOptions As Inventor.NameValueMap =
            ThisApplication.TransientObjects.CreateNameValueMap()

        If oPDFAddIn.HasSaveCopyAsOptions(oDoc, oContext, oOptions) Then
            oOptions.Value("All_Color_AS_Black") = 1
            oOptions.Value("Remove_Line_Weights") = 0
            oOptions.Value("Vector_Resolution") = 400
            oOptions.Value("Sheet_Range") = Inventor.PrintRangeEnum.kPrintAllSheets
        End If

        Dim oData As Inventor.DataMedium =
            ThisApplication.TransientObjects.CreateDataMedium()
        oData.FileName = pdfPath

        oPDFAddIn.SaveCopyAs(oDoc, oContext, oOptions, oData)

    Catch ex As Exception
        MessageBox.Show("Error exportando PDF: " & ex.Message, "iLogic PDF")
    End Try
End Sub

Function TryGetParamMM(ByVal refDoc As Inventor.Document, ByVal pName As String, ByRef valOut As Double) As Boolean
    Try
        Dim p As Inventor.Parameter = refDoc.ComponentDefinition.Parameters.Item(pName)
        Dim uom = refDoc.UnitsOfMeasure
        valOut = uom.ConvertUnits(p.Value, uom.LengthUnits, Inventor.UnitsTypeEnum.kMillimeterLengthUnits)
        Return True
    Catch
        Return False
    End Try
End Function

Function TryGetParamUnitless(ByVal refDoc As Inventor.Document, ByVal pName As String, ByRef valOut As Double) As Boolean
    Try
        Dim p As Inventor.Parameter = refDoc.ComponentDefinition.Parameters.Item(pName)
        valOut = p.Value
        Return True
    Catch
        Return False
    End Try
End Function
