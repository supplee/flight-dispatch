# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'confirmadd.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(300, 200)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(0, 160, 280, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.No|QtWidgets.QDialogButtonBox.Yes)
        self.buttonBox.setCenterButtons(True)
        self.buttonBox.setObjectName("buttonBox")
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setGeometry(QtCore.QRect(100, 120, 111, 16))
        font = QtGui.QFont()
        font.setFamily("DejaVu Math TeX Gyre")
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.groupBox = QtWidgets.QGroupBox(Dialog)
        self.groupBox.setGeometry(QtCore.QRect(10, 0, 281, 151))
        font = QtGui.QFont()
        font.setFamily("DejaVu Math TeX Gyre")
        self.groupBox.setFont(font)
        self.groupBox.setTitle("")
        self.groupBox.setAlignment(QtCore.Qt.AlignCenter)
        self.groupBox.setObjectName("groupBox")
        self.flightLabel = QtWidgets.QLabel(self.groupBox)
        self.flightLabel.setGeometry(QtCore.QRect(0, 39, 281, 71))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.flightLabel.setFont(font)
        self.flightLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.flightLabel.setObjectName("flightLabel")
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(70, 20, 141, 16))
        self.label.setObjectName("label")
        self.groupBox.raise_()
        self.buttonBox.raise_()
        self.label_3.raise_()

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Confirmation"))
        self.label_3.setText(_translate("Dialog", "to your itinerary?"))
        self.flightLabel.setText(_translate("Dialog", "US1549 (KLGA - KCLT)"))
        self.label.setText(_translate("Dialog", "Would you like to add:"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())

