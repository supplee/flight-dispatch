# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QSortFilterProxyModel
from PyQt5.QtWidgets import QMainWindow, QAbstractItemView
from models.datamodel import ModelMetaData as FlightData
from models.datamodel import FlightQuery
from models.datamodel import ORMConstruction
from models.datamodel import Results
from models.datamodel import Itinerary
from views.dispatcher import Ui_MainWindow
from datetime import datetime
#import views.itinerary

import re

class PandasModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    """
    def __init__(self, data, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data.values)

    def columnCount(self, parent=None):
        return self._data.columns.size

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self._data.values[index.row()][index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._data.columns[col]
        #if role == QtCore.Qt.DisplayRole:
        #    return self._data.columns[col]
        return None

class ItineraryWindow(QMainWindow): # ,views.itinerary.Ui_MainWindow) <-- add to inherit from pre-compiled window once UI is complete
    def __init__(self, itinerary, parent=None):
        super(ItineraryWindow,self).__init__(parent)
        #self.setupUi(self) <-- uncomment to inherit from pre-compiled object once UI is complete
        uic.loadUi('views/itinerary.ui', self) # <-- Use temporarily while UI is still being changed.
        self.itinerary = itinerary
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableView.customContextMenuRequested.connect(self.on_rightClickFlight)
        self.loadModel()
        self.statusbar.showMessage('Right click a flight to remove it from your itinerary ...')
        self.actionSaveItinerary.triggered.connect(self.on_saveFile)
        self.actionOpenItinerary.triggered.connect(self.on_openFile)
        self.fileName = ''
        self.parent = parent
    
    def on_rightClickFlight(self, pos):
        self.flightMenu = QtWidgets.QMenu(self)
        removeAction = self.flightMenu.addAction('Remove')
        #self.flightMenu.removeAction.clicked.connect(self.on_removeFlight)
        action = self.flightMenu.exec_(self.tableView.viewport().mapToGlobal(pos))
        if action == removeAction:
            self.on_removeFlight()

    def on_removeFlight(self):
        selectedIndex=self.tableView.currentIndex()
        thisRow = selectedIndex.row()
        self.itinerary.remove(thisRow)
        self.loadModel()
    
    def on_saveFile(self):
        if not self.itinerary.file:
            saveDialog = QtWidgets.QFileDialog()
            if len(self.itinerary.df.index)>0:
                suggestedFileName = self.itinerary.df.Airline.mode()[0]
                suggestedFileName.replace(' ','')
                suggestedFileName += '-'
                selectedDate = self.parent.depCalendar.selectedDate()
                suggestedFileName += '{0}-{1}-{2}'.format(selectedDate.day(),selectedDate.month(),selectedDate.year())
                suggestedFileName += '-flightcrew1'
                suggestedFileName += '.xlsx'

            fileName = saveDialog.getSaveFileName(self, 'Save File', suggestedFileName, 'Microsoft Excel (*.xlsx)')[0]
            if fileName.rfind('.') < 0:
                fileName += '.xlsx'
        else:
            fileName = self.itinerary.file
            
        if self.itinerary.save(fileName):
            return self.showMsg('Itinerary saved as {}'.format(self.itinerary.file))
        else:
            return self.showMsg('Failed to save file!',warning=True)

    def on_openFile(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        (fileName, _) = QtWidgets.QFileDialog.getOpenFileName(self,'Open a previously saved itinerary', '', 'Microsoft Excel (*.xlsx)')
        if fileName.rfind('.') < 0:
            fileName += '.xlsx'
        if len(fileName) <= 5:
            return

        if not self.itinerary.open(fileName):
            return self.showMsg('I could not access that file, or the contents could not be interpreted!',warning=True)
        else:
            self.loadModel()

    def showMsg(self, text, warning=False):
        self.msgbox = QtWidgets.QMessageBox()
        if not warning:
            self.msgbox.setIcon(QtWidgets.QMessageBox.Information)
            self.msgbox.setWindowTitle("FYI Bro!")
        else:
            self.msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            self.msgbox.setWindowTitle("We have a big fucking problem!")
        self.msgbox.setText(text)

        self.msgbox.show()

    def loadModel(self):
        """
        Reloads the tableView from our underlying pandas dataframe each time the data is updated
        """
        tableModel = PandasModel(self.itinerary.model())
        #proxyModel = QSortFilterProxyModel()
        #proxyModel.setSourceModel(tableModel)
        #proxyModel.setFilterKeyColumn(4)
        self.tableView.setModel(tableModel)
        #self.tableView.setSortingEnabled(True)
        self.tableView.show()
        self.loadAnalytics()
    
    def loadAnalytics(self):
        data = self.itinerary.model()
        etelist = data['ETE']
        etelist = etelist.to_list()
        hours = []
        minutes = []
        for e in etelist:
            (hour,minute) = e.split(':',2)
            hours.append(int(hour))
            minutes.append(int(minute))
        hours = sum(hours)
        minutes = sum(minutes)
        (moreHours,remMins) = divmod(minutes,60)
        hours += moreHours
        minutes = remMins

        self.flightTimeLabel.setText('{:02d}:{:02d}'.format(hours,minutes))
    
    def closeEvent(self, event):
        del(self.itinerary)
        del(self.parent.itinerary)
        self.parent.itinerary = Itinerary()
        del(self.parent.iWindow)
        event.accept()
    

class AddFlightDialogVM(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(AddFlightDialogVM,self).__init__(parent)
        uic.loadUi('views/confirmadd.ui', self)

class dispatch_PopulateThread(QtCore.QThread):
    dataRetrieved = QtCore.pyqtSignal(list, list)
    def __init__(self, icao_dep='.*', icao_arr='.*', parent=None):
        super(dispatch_PopulateThread,self).__init__(parent)
        self.icao_dep = icao_dep
        self.icao_arr = icao_arr
    
    def run(self):
        flightData = FlightData()
        query = FlightQuery(icao_dep=self.icao_dep,icao_arr=self.icao_arr)
        query.flush(method='nosql')
        airlines = query.df.airline.unique()
        airlines = [x.strip(' ') for x in airlines]
        airlines.sort()
        

        aircraftList = query.df.aircraft.unique()
        aircraftList = [x.strip(' ') for x in aircraftList]
        aircraftList.sort()

        self.dataRetrieved.emit(airlines, aircraftList)

class dispatch_SearchThread(QtCore.QThread):
    dataRetrieved = QtCore.pyqtSignal(Results)

    def __init__(self, airline='.*',icao_dep='.*',icao_arr='.*',aircraft='.*',departing='.*',weekdayId=range(0,7), parent=None):
        super(dispatch_SearchThread,self).__init__(parent)
        self.icao_dep = icao_dep
        self.icao_arr = icao_arr
        self.airline = airline
        self.aircraft = aircraft
        self.departing = departing
        self.weekdayId = weekdayId

    def run(self):
        query = FlightQuery(airline=self.airline,icao_dep=self.icao_dep,icao_arr=self.icao_arr,aircraft=self.aircraft,departing=self.departing,weekdayId=self.weekdayId)
        resultObject = query.flush(method='sql')
        self.dataRetrieved.emit(resultObject)

class DispatchWindowVM(QMainWindow):
    def __init__(self, parent=None):
        super(DispatchWindowVM,self).__init__(parent)
        uic.loadUi('views/dispatcher.ui', self)
        self.depFilter.setText('KSFO')
        self.searchButton.clicked.connect(self.buildSearchFromUI)
        self.cbThread = dispatch_PopulateThread()
        self.cbThread.dataRetrieved.connect(self.constructComboBoxes)
        self.cbThread.start()
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.doubleClicked.connect(self.selectFlight)
        self.buildSearchFromUI()
        self.itinerary = Itinerary()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.depCalendar.repaint)
        self.timer.start(2000)

    def selectFlight(self):
        selectedIndex=self.tableView.currentIndex()
        thisRow = selectedIndex.row()
        header = self.tableView.horizontalHeader().model()
        labels = []
        values = []
        i=0
        for column in range(header.columnCount()):
            labels.append(header.headerData(column, QtCore.Qt.Horizontal))
            cellIndex = self.tableView.model().index(thisRow, i)
            cellValue = self.tableView.model().data(cellIndex)
            values.append(cellValue)
            i += 1

        self.confirmDialog = AddFlightDialogVM()
        self.confirmDialog.flightLabel.setText(values[0]+" ("+values[3]+"-"+values[5]+")")
        self.confirmDialog.buttonBox.accepted.connect(lambda h=labels,v=values: self.saveFlight(h,v))
        self.confirmDialog.show()

    def saveFlight(self, labels, values):
        self.itinerary.add(labels,values)
        self.updateItineraryVM(self.itinerary)

    def constructComboBoxes(self,airlines,aircraftList):
        self.airlineFilter.clear()
        self.airlineFilter.addItem("Any")
        self.airlineFilter.addItems(airlines)

        self.aircraftFilter.clear()
        self.aircraftFilter.addItem("Any")
        self.aircraftFilter.addItems(aircraftList)

    def updateResults(self, tableModel):
        proxyModel = QSortFilterProxyModel()
        proxyModel.setSourceModel(tableModel)
        #proxyModel.setFilterKeyColumn(4)
        self.tableView.setModel(proxyModel)
        self.tableView.setSortingEnabled(True)
        self.tableView.show()
    
    def buildSearchFromUI(self):
        flightData = FlightData()
        weekday = self.depCalendar.selectedDate().toString()[0:3]
        weekdayId = [flightData.dayIndex[weekday]]
        icao_dep = self.depFilter.text()
        icao_dep = icao_dep.upper()
        wildcard = r'[^\.][\*]'
        for match in re.finditer(wildcard,icao_dep):
            initialCharacter = str(match.group(0)[0])
            icao_dep = re.sub(wildcard,initialCharacter+'%',icao_dep,1)
        if icao_dep == '':
            icao_dep = '%'
        if icao_dep[0] == '*':
            icao_dep = '%' + icao_dep
        icao_arr = self.arrFilter.text()
        icao_arr = icao_arr.upper()
        for match in re.finditer(wildcard,icao_arr):
            initialCharacter = str(match.group(0)[0])
            icao_arr = re.sub(wildcard,initialCharacter+'%',icao_arr,1)
        if icao_arr == '':
            icao_arr = '%'
        if icao_arr[0] == '*':
            icao_arr = '%'+icao_arr

        airline = str(self.airlineFilter.currentText())
        if airline == 'Any':
            airline = "%"
        
        aircraft = str(self.aircraftFilter.currentText())
        if aircraft == 'Any':
            aircraft = "%"
        
        departing = str(self.depTime.currentText())
        if departing == 'Any':
            departing = '%'
        
        self.statusbar.showMessage("Searching... | NOTE: Long load times are caused by search criteria that are too broad.  Consider narrowing your search.")
        self.searchThread = dispatch_SearchThread(airline=airline,icao_dep=icao_dep,icao_arr=icao_arr,aircraft=aircraft,departing=departing,weekdayId=weekdayId)
        self.searchThread.dataRetrieved.connect(self.displaySearchResults)
        self.searchThread.start()

    def displaySearchResults(self, resultObject):
        #self.showDebugMsg(icao_dep + icao_arr + departing + airline + aircraft + str(weekdayId[0]))
        resultModel = PandasModel(resultObject.displayTable())
        self.updateResults(resultModel)
        self.statusbar.showMessage("Loaded " + str(resultModel.rowCount()) + " results | Double click a result to add it to your itinerary")

    def showDebugMsg(self, text):
        self.warning = QtWidgets.QMessageBox()
        self.warning.setIcon(QtWidgets.QMessageBox.Information)
        self.warning.setText(text)
        self.warning.setWindowTitle("Debug Information")
        self.warning.show()
    
    def updateItineraryVM(self, itinerary):
        try:
            self.iWindow.itinerary = self.itinerary
            self.iWindow.loadModel()
        except:
            self.iWindow = ItineraryWindow(itinerary, self)
            self.iWindow.show()
    



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # DispatchWindow = QtWidgets.QMainWindow()
    ORMConstruction()
    mainVM = DispatchWindowVM()
    
    mainVM.depFilter.setText("KSFO")
    mainVM.show()
        
    sys.exit(app.exec_())

