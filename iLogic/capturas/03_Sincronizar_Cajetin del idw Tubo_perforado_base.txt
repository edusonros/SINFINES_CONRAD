'========================================
' 03_Sincronizar_Cajetin
' Fuerza actualización de iProperties y cajetín
'========================================

Try
    Dim oDraw As DrawingDocument = ThisApplication.ActiveDocument
    
    ' Actualiza referencias (asegura que lee iProperties recientes)
    oDraw.Update()

    ' Fuerza actualización de Title Block / cajetín
    For Each s As Sheet In oDraw.Sheets
        s.TitleBlock.Definition.Sketch.Edit()
        s.TitleBlock.Definition.Sketch.ExitEdit()
    Next

    oDraw.Update()

Catch ex As Exception
    MessageBox.Show("Error sincronizando cajetín: " & ex.Message, "iLogic")
End Try
