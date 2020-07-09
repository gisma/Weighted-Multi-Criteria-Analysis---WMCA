# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MultiCriteria
                                 A QGIS plugin
 Displays raster’s pixels values to the user, making possible to assign weights
 for each raster and grades for each class within each raster.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-07-03
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Carvalho Neto, R.M./ UFSM and Benedetti, A.C.P./ UFSM
        email                : romariocarvalho@hotmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5 import QtGui
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QTableWidget, QDialog, QProgressBar, QComboBox
from PyQt5.QtWidgets import *
from qgis.core import QgsProject, QgsTask, QgsApplication, Qgis
from qgis.utils import iface
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .multi_criteria_dialog import MultiCriteriaDialog
import os.path
# modules for the calculus
from osgeo import gdal
import osr
import numpy as np
import os # This is needed in the pyqgis console also


class MultiCriteria:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'MultiCriteria_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
            # if qVersion() > '4.3.3':
                # QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Weighted Multi-Criteria Analysis - WMCA') #adds the name to the menu, in our case the raster menu 

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MultiCriteria', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/multi_criteria/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Weighted Multi-Criteria Analysis - WMCA'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&Weighted Multi-Criteria Analysis - WMCA'),
                action)
            self.iface.removeToolBarIcon(action)


    def select_input_raster(self):
        """Selects the input for the evaluation and display on table"""
        row_number = 0
        column_number = 0
        nomeRaster = self.dlg.mMapLayerComboBox.currentText()
        layer_selecionado = self.dlg.mMapLayerComboBox.currentLayer() # gets the selected layer
        if layer_selecionado == None:
            message = QCoreApplication.translate('Message to user','Load Rasters to QGIS first')
            QMessageBox.warning(self.dlg,QCoreApplication.translate('Message to user','Missing Information'), message)
        elif layer_selecionado.type() == layer_selecionado.RasterLayer:
            rasterPathCompleto = layer_selecionado.source()

            rasterOpen = gdal.Open(rasterPathCompleto)
            rasterUso = rasterOpen.GetRasterBand(1)
            noData_daFuncao = rasterUso.GetNoDataValue()
            if noData_daFuncao == None:
                noData_daFuncao = -9999
            self.listaNoData.append(noData_daFuncao)
            MultiCriteria.noData = self.listaNoData[0] #will work with the noData from the first raster selected
            arrayUso = np.array(rasterUso.ReadAsArray())
            
            #------ Check the size of the raster
            carregar = True
            if len(np.unique(arrayUso)) > 100: # don't accept if more than 100 classes
                message = QCoreApplication.translate('Message to user','The raster has more than 100 classes. Use the "Reclassify by table" from the QGIS tools to decrease the number of classes')
                QMessageBox.warning(self.dlg,QCoreApplication.translate('Message to user','Missing Information'), message)
                carregar = False
            elif len(np.unique(arrayUso)) > 50 and len(np.unique(arrayUso)) <= 100:
                message = QCoreApplication.translate('Message to user','The raster has more than 50 classes and may take some time to load. It\'s possible to group classes of a raster following the instructions on the right, or by using the "Reclassify by table" from the QGIS tools')
                QMessageBox.warning(self.dlg,QCoreApplication.translate('Message to user','Missing Information'), message)
           
            if carregar:
                MultiCriteria.listaLayersSelecionados.append(layer_selecionado)
                self.listaAssert.append((rasterOpen.RasterXSize,rasterOpen.RasterYSize)) #(X,Y)
                if len(MultiCriteria.listaLayersSelecionados) == 1:
                    #------ Creates the table
                    self.tabelaNotas = QTableWidget()
                    self.dlg.tableWidget.insertRow(row_number)
                    self.dlg.tableWidget.setItem(row_number, column_number, QTableWidgetItem(str(nomeRaster)))
                    self.dlg.tabWidget.addTab(self.tabelaNotas,nomeRaster)
                    self.tabelaNotas.insertColumn(0)
                    self.tabelaNotas.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
                    self.tabelaNotas.setHorizontalHeaderItem(0, QTableWidgetItem(QCoreApplication.translate("Tab title","Original Value")))
                    self.tabelaNotas.insertColumn(1)
                    self.tabelaNotas.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
                    self.tabelaNotas.setHorizontalHeaderItem(1, QTableWidgetItem(QCoreApplication.translate("Tab title","Grade")))
                    self.tabelaNotas.insertColumn(2)
                    self.tabelaNotas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
                    self.tabelaNotas.setHorizontalHeaderItem(2, QTableWidgetItem(QCoreApplication.translate("Tab title","Disregard")))
 
                    # ------ load the unique values of raster on table for user to give grades     
                    for elementoUnico in sorted(np.unique(arrayUso),reverse=True):
                        if elementoUnico != MultiCriteria.noData:
                            self.desconsiderarCheckBox = QCheckBox(QCoreApplication.translate("Tab","Not Calculate"))
                            self.tabelaNotas.insertRow(row_number) 
                            self.tabelaNotas.setCellWidget(row_number,2,self.desconsiderarCheckBox)
                            item = QTableWidgetItem(str(elementoUnico))
                            flags = Qt.ItemIsEnabled  # set not editable 
                            item.setFlags(flags)
                            self.tabelaNotas.setItem(row_number, column_number, item)

                else:
                    mensagem = "erro raster{}".format(str(len(self.listaAssert)))
                    try:
                        assert(self.listaAssert[0] == self.listaAssert[-1]), mensagem
                    
                        #------ Creates the table
                        self.tabelaNotas = QTableWidget()
                        self.dlg.tableWidget.insertRow(row_number)
                        self.dlg.tableWidget.setItem(row_number, column_number, QTableWidgetItem(str(nomeRaster)))
                        self.dlg.tabWidget.addTab(self.tabelaNotas,nomeRaster)
                        self.tabelaNotas.insertColumn(0)
                        self.tabelaNotas.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
                        self.tabelaNotas.setHorizontalHeaderItem(0, QTableWidgetItem(QCoreApplication.translate("Tab title","Original Value")))
                        self.tabelaNotas.insertColumn(1)
                        self.tabelaNotas.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
                        self.tabelaNotas.setHorizontalHeaderItem(1, QTableWidgetItem(QCoreApplication.translate("Tab title","Grade")))
                        self.tabelaNotas.insertColumn(2)
                        self.tabelaNotas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
                        self.tabelaNotas.setHorizontalHeaderItem(2, QTableWidgetItem(QCoreApplication.translate("Tab title","Disregard")))

                        # ------ load the unique values of raster on table for user to give grades     
                        for elementoUnico in sorted(np.unique(arrayUso),reverse=True):
                            if elementoUnico != MultiCriteria.noData:
                                self.desconsiderarCheckBox = QCheckBox(QCoreApplication.translate("Tab","Not Calculate"))
                                self.tabelaNotas.insertRow(row_number) 
                                self.tabelaNotas.setCellWidget(row_number,2,self.desconsiderarCheckBox)
                                item = QTableWidgetItem(str(elementoUnico))
                                flags = Qt.ItemIsEnabled  # set not editable 
                                item.setFlags(flags)
                                self.tabelaNotas.setItem(row_number, column_number, item) 
                                                
                    except:
                        traduzir = QCoreApplication.translate('Message to user','The previous raster(s) has {} X cells and {} Y cells while this last raster \'{}\' has {} X cells and {} Y cells. They are not the same size. It will not be added to the Evaluation.')
                        message = traduzir.format(str(self.listaAssert[0][0]),
                                                str(self.listaAssert[0][1]),
                                                str(nomeRaster),
                                                str(self.listaAssert[-1][0]),
                                                str(self.listaAssert[-1][1]))
                        QMessageBox.warning(self.dlg,QCoreApplication.translate('Message to user','Missing Information'), message)
                        MultiCriteria.listaLayersSelecionados.pop(-1)
                        self.listaAssert.pop(-1)

        else:
            message = QCoreApplication.translate('Message to user','Select only rasters')
            QMessageBox.warning(self.dlg,QCoreApplication.translate('Message to user','Missing Information'), message)
                     

    def remove_input_raster(self):
        """Removes the selected line and its table in the next page"""
        selecionado = self.dlg.tableWidget.currentRow()
        if selecionado == -1: #only to not have an error message if no layer was selected
            pass
        else:
            self.dlg.tableWidget.removeRow(selecionado)
            nRows = self.dlg.tableWidget.rowCount()
            indexTab_remover = (nRows) - selecionado #the index of tab is inverse to the index of lines
            self.dlg.tabWidget.removeTab(indexTab_remover)
            MultiCriteria.listaLayersSelecionados.pop(indexTab_remover)
            self.listaNoData.pop(indexTab_remover)
            self.listaAssert.pop(indexTab_remover)


    def select_output_file(self):
        """Selects the output path and name"""
        filename, _filter = QFileDialog.getSaveFileName(
            self.dlg, QCoreApplication.translate('output',"Select the output folder and the raster name"),"", '*.tif') 
        self.dlg.lineEdit.setText(filename)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            #self.first_start = False
            self.dlg = MultiCriteriaDialog()
            self.dlg.tabWidget.clear() #cleans the two tabs that came default
        
        self.listaNoData = []
                
        # Fetch the currently loaded layers                                          
        # layer_instance = QgsProject.instance()
        # layers = layer_instance.layerTreeRoot().children()          
        # Clear the contents of the comboBox from previous runs                      
        # self.dlg.mMapLayerComboBox.clear()                                 
        # # Populate the comboBox with names of all the loaded layers                  
        # self.listaNomeRasters = [layer.name() for layer in layers]
        # self.dlg.mMapLayerComboBox.addItems(self.listaNomeRasters)
        # list of rasters to update the layer to take its path
        MultiCriteria.listaLayersSelecionados = [] #list of selected layers
        self.listaAssert = [] #list to assert raster size
        self.dlg.addRasterButton.clicked.connect(self.select_input_raster)  #adds the raster name(and more)to the table
        self.dlg.removeRasterButton.clicked.connect(self.remove_input_raster)#removes the raster name(and more)from the table
        self.dlg.pushButton.clicked.connect(self.select_output_file)
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            
            MultiCriteria.adress = self.dlg.lineEdit.text()

            #----------- getting the typed values ----------------------------
            
            nColunasPeso = self.dlg.tableWidget.columnCount()#  <----
            nRowsPeso = self.dlg.tableWidget.rowCount()#  <----
            
            MultiCriteria.listaPesos = [[] for raster in range(nRowsPeso)]  #  <----
            
            for linhas in range(nRowsPeso):
                for colunas in range(nColunasPeso):
                    itemValor = self.dlg.tableWidget.item(linhas,colunas) #  <----
                    MultiCriteria.listaPesos[linhas].insert(0,itemValor.text())
            
            MultiCriteria.listaNotas = []  # list to contain the grades from the dialog box
            
            # ------ Build a list to get the pixel value and its corresponding given grade            
            for raster in range(nRowsPeso):  
                MultiCriteria.listaNotas.append([]) #adds inside the list, a [] space to put the chosen rasters
                aba_tabela_Notas = self.dlg.tabWidget.widget(raster) #  <----
                nClasse = aba_tabela_Notas.rowCount()  
                for linhas in range(nClasse): 
                    MultiCriteria.listaNotas[raster].append([]) #adds inside the raster list, a [] space to put the chosen classes within each raster
                    checkBox_cel = aba_tabela_Notas.cellWidget(linhas,2) #  <----
                    for colunas in range(2): # number of columns (3): raster pixel value, grade and "not considered" 
                        itemValor = aba_tabela_Notas.item(linhas,colunas) #  <----
                        if checkBox_cel.isChecked():
                            if colunas == 1:
                                MultiCriteria.listaNotas[raster][linhas].append(-9998)
                            else:
                                MultiCriteria.listaNotas[raster][linhas].append(itemValor.text())
                        else:
                            MultiCriteria.listaNotas[raster][linhas].append(itemValor.text())

            MultiCriteria.progress_bar = ProgessBar()
            MultiCriteria.progress_bar.show()
            #MultiCriteria.progress_bar.newTask('Calculating...')


class HeavyTask(QgsTask):
    """Here we subclass QgsTask"""
    def __init__(self, desc):
        QgsTask.__init__(self, desc)


    def raster2arrayNotas(self, rasterEntradaPath, listaEntradaNotas):
        """Turns a raster into a array and replace pixel values by the grades"""
        #--------------- transforming input rasters in arrays -----------------------

        rasterOpen = gdal.Open(rasterEntradaPath) 
        rasterUso = rasterOpen.GetRasterBand(1)
        rasterUso.SetNoDataValue(MultiCriteria.noData)
        arrayUso = np.array(rasterUso.ReadAsArray())
        
        #---------------------------- New grades ----------------------------------------   

        arrayNota = [ [] for row in arrayUso ] #array with new values
        
        #--- calculate a aprox size to put in the progress bar
        amount = len(arrayUso) * len(arrayUso[0])
        bit = self.div / amount    # max percentage until this point - last point / len
        prog = self.chunk # self.chunk changes but self.div dont
        #-------------------

        for row in range(len(arrayUso)):
            for pixel in arrayUso[row]:
                #--- calculate a aprox size to put in the progress bar
                self.setProgress(prog)
                prog += bit
                #-----------------------------------------------------
                if pixel == MultiCriteria.noData: #keep the nodata in place
                    arrayNota[row].append(MultiCriteria.noData)
                else:
                    for substituicao in range(len(listaEntradaNotas)):
                        valorPixel = listaEntradaNotas[substituicao][0] 
                        notaRecebida = listaEntradaNotas[substituicao][1]
                        if pixel == np.float32(valorPixel):
                            try:
                                arrayNota[row].append(float(notaRecebida)) # add the grade value
                            except:
                                arrayNota[row].append(float(-9998))# if there is a string, for exemplo,
                        else:                                      # it will be replaced by a blocked
                            pass
        return arrayNota


    def array2raster(self, rasterfn, newRasterfn, array):  #rasterfn: name and path to model raster 
        """Turns a array into a raster"""                  #newRasterfn: name and path to new raster
        raster = gdal.Open(rasterfn) #raster model         #array: array with new values to became raster
        geotransform = raster.GetGeoTransform()
        originX = geotransform[0] 
        originY = geotransform[3]
        pixelWidth = geotransform[1]
        pixelHeight = geotransform[5]
        cols = raster.RasterXSize
        rows = raster.RasterYSize
        driver = gdal.GetDriverByName('GTiff')
        outRaster = driver.Create(newRasterfn, cols, rows, 1, gdal.GDT_Float32)
        outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
        outband = outRaster.GetRasterBand(1)
        outband.WriteArray(array)
        outband.SetNoDataValue(MultiCriteria.noData)
        outRasterSRS = osr.SpatialReference()
        outRasterSRS.ImportFromWkt(raster.GetProjectionRef())
        outRaster.SetProjection(outRasterSRS.ExportToWkt())
        outband.FlushCache()


    def run(self):
        """This function is where you do the 'heavy lifting' or implement
        the task which you want to run in a background thread. This function 
        must return True or False and should only interact with the main thread
        via signals"""
        
        percent = 0
        self.setProgress(percent)
       
        #------------------- Input and output of rasters ---------------------
        
        listaPesos_paraCalculos = [] #it needs to be inverted according to the way data is inserted
        
        percent = 0
        for raster in MultiCriteria.listaPesos:
            listaPesos_paraCalculos.insert(0, float(raster[0])) # gets only the grade, in float, for calculation
            #--- calculate a aprox size to put in the progress bar
            amount = len(MultiCriteria.listaPesos)
            div = 10 / amount    # max until this point / len
            percent += div
            self.setProgress(percent)

        listaCalculo = []  # list to have the grades of all rasters for calculation
        
        percent = 10
        self.setProgress(percent)
        # ------ calls raster2arrayNotas() to have at last, a list of grade of each pixel by raster

        #--- calculate a aprox size to put in the progress bar  
        amount = len(MultiCriteria.listaLayersSelecionados)
        self.div = (50-percent) / amount   # max until this point - last point / len
        self.chunk = percent # beggins the point at 10% 
        #-------------------------------------------------------------
        cont = 0
        for layer in MultiCriteria.listaLayersSelecionados:   
            rasterPathCompleto = layer.source()
            pegandoNotas = self.raster2arrayNotas(rasterPathCompleto, MultiCriteria.listaNotas[cont])
            listaCalculo.append(pegandoNotas)
            cont += 1
            self.chunk += self.div  #update the point where at

        percent = 50
        self.setProgress(percent)

        # ------ list to have grade*weight of each pixel by raster
        listaCalculoCelula = [[ [] for row in raster] for raster in listaCalculo ] 

        for raster in range(len(listaCalculo)):
            for row in range(len(listaCalculo[raster])):
                for cel in range(len(listaCalculo[raster][row])):
                    if listaCalculo[raster][row][cel] == MultiCriteria.noData:
                        listaCalculoCelula[raster][row].append(MultiCriteria.noData)
                    elif listaCalculo[raster][row][cel] == -9998:
                        listaCalculoCelula[raster][row].append(-9998)
                    else:
                        # takes the grade of each pixel and * for the weight given to the raster
                        calculoCelula = listaCalculo[raster][row][cel]*listaPesos_paraCalculos[raster]
                        listaCalculoCelula[raster][row].append(calculoCelula)

        percent = 60
        self.setProgress(percent)

        # ----- preparing last array to bacame a raster
        arrayModelo = [[] for row in listaCalculoCelula[0]] #array model to build the output raster

        #--- calculate a aprox size to put in the progress bar
        amount = len(listaCalculoCelula) * len(listaCalculoCelula[0]) * len(listaCalculoCelula[0][0])
        div = (90-percent) / amount   # max until this point - last point / len
        #-------------------------------------------------------------
        for raster in range(len(listaCalculoCelula)):
            for row in range(len(listaCalculoCelula[raster])):
                for cel in range(len(listaCalculoCelula[raster][row])):
                    #---------
                    percent += div
                    self.setProgress(percent)
                    #---------
                    if raster == 0:
                        arrayModelo[row].append(listaCalculoCelula[raster][row][cel])
                    else:
                        if listaCalculoCelula[raster][row][cel] == -9998: # gives priority to "not considered" and any 
                            arrayModelo[row].pop(cel)                     # other value on that cell will be -9998
                            arrayModelo[row].insert(cel,-9998)
                        elif listaCalculoCelula[raster][row][cel] == MultiCriteria.noData:
                            arrayModelo[row].pop(cel)
                            arrayModelo[row].insert(cel,MultiCriteria.noData)
                        else:
                            if arrayModelo[row][cel] == -9998:  # also gives priority to "not considered" and any
                                pass #it continues -9998            # other value on that cell will be -9998
                            elif arrayModelo[row][cel] == MultiCriteria.noData:
                                if listaCalculoCelula[raster][row][cel] == -9998:
                                    arrayModelo[row].pop(cel)         
                                    arrayModelo[row].insert(cel,-9998)#turns nodata into "not considered"
                            else:
                                val = arrayModelo[row].pop(cel) # pop return the taken value
                                arrayModelo[row].insert(cel,(val+listaCalculoCelula[raster][row][cel]))
        
        percent = 90
        self.setProgress(percent)

        # ----------------------- Building final raster -------------------------------

        rasterModelPathCompleto = MultiCriteria.listaLayersSelecionados[0].source() # takes first raster chosen as model
        self.rasterAvalicaoPath = MultiCriteria.adress
        self.array2raster(rasterModelPathCompleto,self.rasterAvalicaoPath,np.array(arrayModelo))
        
        percent = 100
        self.setProgress(percent)
        return True


    def finished(self, result):
        """This function is called automatically when the task is completed and is
        called from the main thread so it is safe to interact with the GUI etc here"""
        if result is False:
            iface.messageBar().pushMessage('Task was cancelled')
        else:
            iface.addRasterLayer(self.rasterAvalicaoPath)
            iface.messageBar().pushMessage('Complete')
            #ProgessBar.btn_cancel.setEnabled(False)



class ProgessBar(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.resize(310, 140)
        self.lbl_info = QLabel('Info:', self) 
        self.lbl_info.move(40, 25) # label with Info
        self.edit_info = QLineEdit(self)
        self.edit_info.resize(170, 20)
        self.edit_info.move(100, 20) # Show changing messages
        self.prog = QProgressBar(self)
        self.prog.resize(230, 30)
        self.prog.move(40, 55) 
        self.newTask('Weighted Multi-Criteria Analysis - WMCA')
        btn_close = QPushButton('Close',self)
        btn_close.move(190, 100)
        btn_close.clicked.connect(self.close_win)
        # ProgessBar.btn_cancel = QPushButton('Cancel Task', self)
        # ProgessBar.btn_cancel.move(40, 100)
        # ProgessBar.btn_cancel.clicked.connect(self.cancelTask)


    def newTask(self, message_task_description):
        """Create a task and add it to the Task Manager"""
        self.task = HeavyTask(message_task_description)
        #connect to signals from the background threads to perform gui operations
        #such as updating the progress bar
        self.task.begun.connect(lambda: self.edit_info.setText("Calculating..."))
        self.task.progressChanged.connect(lambda: self.prog.setValue(self.task.progress()))
        self.task.progressChanged.connect(lambda: self.setProgressBarMessages(self.task.progress()))
        self.task.taskCompleted.connect(lambda: self.edit_info.setText('Complete'))
        self.task.taskTerminated.connect(self.TaskCancelled)
        QgsApplication.taskManager().addTask(self.task)


    def TaskCancelled(self):
        self.prog.setValue(0)
        self.edit_info.setText('Task Cancelled')


    def close_win(self):
        self.close()


    def setProgressBarMessages(self, val):
    # --- Progress bar in the QGIS user messages (top)
        if val <= 15:
            message = "Starting..."
            iface.messageBar().pushMessage(message)
        elif val < 50:
            message = "Calculating according to grades and weights..."
            iface.messageBar().pushMessage(message)
        elif val < 100:
            message = "Preparing final raster..."
            iface.messageBar().pushMessage(message)
        elif val == 100:
            iface.messageBar().clearWidgets()


    # def cancelTask(self):
    #     self.task.cancel()