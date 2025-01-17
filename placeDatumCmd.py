#!/usr/bin/env python3
# coding: utf-8
#
# placeDatumCmd.py


from PySide import QtGui, QtCore
import FreeCADGui as Gui
import FreeCAD as App
import Part, math, re

from libAsm4 import *



"""
    +-----------------------------------------------+
    |                  main class                   |
    +-----------------------------------------------+
"""
class placeDatum( QtGui.QDialog ):
	"My tool object"


	def __init__(self):
		super(placeDatum,self).__init__()
		self.selectedDatum = []


	def GetResources(self):
		return {"MenuText": "Edit Attachment of a Datum object",
				"ToolTip": "Attach a Datum object to an external Part",
				"Pixmap" : os.path.join( iconPath , 'Place_AxisCross.svg')
				}


	def IsActive(self):
		# is there an active document ?
		if App.ActiveDocument:
			# is something selected ?
			if Gui.Selection.getSelection():
				selectedType = Gui.Selection.getSelection()[0].TypeId
				if selectedType=='PartDesign::CoordinateSystem' or selectedType=='PartDesign::Point':
					return True
		else:
			return False 


	"""
    +-----------------------------------------------+
    |                 the real stuff                |
    +-----------------------------------------------+
	"""
	def Activated(self):

		# get the current active document to avoid errors if user changes tab
		self.activeDoc = App.activeDocument()

		# check that we have selected a PartDesign::CoordinateSystem
		selection = self.checkSelectionLCS()
		if not selection:
			self.close()
		else:
			self.selectedDatum = selection


		# Now we can draw the UI
		self.drawUI()
		self.show()


		# check if the datum object is already mapped to something
		# TODO : make a warning and confirmation dialog with "Cancel" and "OK" buttons
		# TODO : see confirmBox below
		if self.selectedDatum.MapMode != 'Deactivated':
			self.selectedDatum.MapMode = 'Deactivated'


		# We get all the App::Link parts in the assembly 
		self.asmParts = []
		# the first item is "Select linked Part" therefore we add an empty object
		self.asmParts.append( [] )
		# find all the linked parts in the assembly
		for obj in self.activeDoc.findObjects("App::Link"):
			if obj.LinkedObject.isDerivedFrom('App::Part'):
				# add it to our tree table if it's a link to an App::Part ...
				self.asmParts.append( obj )
				# ... and add to the drop-down combo box with the assembly tree's parts
				objIcon = obj.LinkedObject.ViewObject.Icon
				self.parentList.addItem( objIcon, obj.Name, obj)


		# get and store the current expression engine:
		self.old_EE = ''
		old_EE = self.selectedDatum.ExpressionEngine
		if old_EE:
			( pla, self.old_EE ) = old_EE[0]

		# decode the old ExpressionEngine
		# if the decode is unsuccessful, old_Expression is set to False
		# and old_attPart and old_attLCS are set to 'None'
		old_Parent = ''
		old_ParentPart = ''
		old_attLCS = ''
		( old_Parent, old_ParentPart, old_attLCS ) = splitExpressionDatum( self.old_EE )
		#self.expression.setText( 'old_Parent = '+ old_Parent )


		# find the oldPart in the part list...
		oldPart = self.parentList.findText( old_Parent )
		# if not found
		if oldPart == -1:
			self.parentList.setCurrentIndex( 0 )
		else:
			self.parentList.setCurrentIndex( oldPart )
			# this should have triggered self.getPartLCS() to fill the LCS list


		# find the oldLCS in the list of LCS of the linked part...
		lcs_found = []
		lcs_found = self.attLCSlist.findItems( old_attLCS, QtCore.Qt.MatchExactly )
		if lcs_found:
			# ... and select it
			self.attLCSlist.setCurrentItem( lcs_found[0] )
		else:
			# may-be it was renamed, see if we can find it as (name)
			lcs_found = self.attLCSlist.findItems( '('+old_attLCS+')', QtCore.Qt.MatchContains )
			if lcs_found:
				self.attLCSlist.setCurrentItem( lcs_found[0] )



		#self.msgBox = QtGui.QMessageBox()
		#self.msgBox.setWindowTitle('Warning')
		#self.msgBox.setIcon(QtGui.QMessageBox.Critical)
		#self.msgBox.setText("Activated placeLCSCmd")
		#self.msgBox.exec_()
		#FreeCAD.activeDocument().Tip = FreeCAD.activeDocument().addObject('App::Part','Model')
		#FreeCAD.activeDocument().getObject('Model').newObject('App::DocumentObjectGroup','Constraints')
		#FreeCAD.activeDocument().getObject('Model').newObject('PartDesign::CoordinateSystem','LCS_0')



	"""
    +-----------------------------------------------+
    | check that all necessary things are selected, |
    |   populate the expression with the selected   |
    |    elements, put them into the constraint     |
    |   and trigger the recomputation of the part   |
    +-----------------------------------------------+
	"""
	def onApply(self):
		# get the name of the part to attach to:
		# it's either the top level part name ('Model')
		# or the provided link's name.
		if self.parentList.currentIndex() > 0:
			parent = self.asmParts[ self.parentList.currentIndex() ]
			a_Link = parent.Name
			a_Part = parent.LinkedObject.Document.Name
		else:
			a_Link = None
			a_Part = None


		# the attachment LCS's name in the parent
		# check that something is selected in the QlistWidget
		if self.attLCSlist.selectedItems():
			a_LCS = self.attLCStable[ self.attLCSlist.currentRow() ].Name
		else:
			a_LCS = None

		# check that all of them have something in
		# constrName has been checked at the beginning
		if not a_Part or not a_LCS :
			self.expression.setText( 'Problem in selections' )
		else:
			# don't forget the last '.' !!!
			# <<LinkName>>.Placement.multiply( <<LinkName>>.<<LCS.>>.Placement )
			# expr = '<<'+ a_Part +'>>.Placement.multiply( <<'+ a_Part +'>>.<<'+ a_LCS +'.>>.Placement )'
			expr = makeExpressionDatum( a_Link, a_Part, a_LCS )
			# this can be skipped when this method becomes stable
			self.expression.setText( expr )
			# load the built expression into the Expression field of the constraint
			self.activeDoc.getObject( self.selectedDatum.Name ).setExpression( 'Placement', expr )
			# recompute the object to apply the placement:
			self.selectedDatum.recompute()
			# highlight the selected LCS in its new position
			Gui.Selection.clearSelection()
			Gui.Selection.addSelection( self.activeDoc.Name, 'Model', self.selectedDatum.Name +'.')
		return



	"""
    +-----------------------------------------------+
    |   find all the linked parts in the assembly   |
    +-----------------------------------------------+

	def getAllLinkedParts(self):
		allLinkedParts = [ ]
		for obj in self.activeDoc.findObjects("App::Link"):
			# add it to our list if it's a link to an App::Part
			if obj.LinkedObject.isDerivedFrom('App::Part'):
				allLinkedParts.append( obj )
		return allLinkedParts
	"""

	"""
    +-----------------------------------------------+
    |           get all the LCS in a part           |
    +-----------------------------------------------+
	"""
	def getPartLCS( self, part ):
		partLCS = [ ]
		# parse all objects in the part (they return strings)
		for objName in part.getSubObjects():
			# get the proper objects
			# all object names end with a "." , this needs to be removed
			obj = part.getObject( objName[0:-1] )
			if obj.TypeId == 'PartDesign::CoordinateSystem' or obj.TypeId == 'PartDesign::Point':
				partLCS.append( obj )
		return partLCS


	"""
    +------------------------------------------------+
    |   fill the LCS list when changing the parent   |
    +------------------------------------------------+
	"""
	def onParentList(self):
		# clear the LCS list
		self.attLCSlist.clear()
		self.attLCStable = []
		# clear the selection in the GUI window
		Gui.Selection.clearSelection()
		# the current text in the combo-box is the link's name...
		parentName = self.parentList.currentText()
		parentPart = self.activeDoc.getObject( parentName )
		if parentPart:
			# we get the LCS from the linked part
			self.attLCStable = self.getPartLCS( parentPart.LinkedObject )
			self.parentDoc.setText( parentPart.LinkedObject.Document.Name )
			# highlight the selected part:
			Gui.Selection.addSelection( parentPart.Document.Name, 'Model', parentPart.Name+'.' )
		# build the list
		for lcs in self.attLCStable:
			newItem = QtGui.QListWidgetItem()
			# if the LCS has been renamed, we show both the label and the (name)
			if lcs.Name == lcs.Label:
				newItem.setText( lcs.Name )
			else:
				newItem.setText( lcs.Label + ' (' +lcs.Name+ ')' )
			newItem.setIcon( lcs.ViewObject.Icon )
			self.attLCSlist.addItem( newItem )
		return





	"""
    +-----------------------------------------------+
    |  An LCS has been clicked in 1 of the 2 lists  |
    |              We highlight both LCS            |
    +-----------------------------------------------+
	"""
	def onDatumClicked( self ):
		# clear the selection in the GUI window
		Gui.Selection.clearSelection()
		# check that something is selected
		if self.attLCSlist.selectedItems():
			# get the linked part where the selected LCS is
			a_Part = self.parentList.currentText()
			# LCS in the linked part
			a_LCS = self.attLCStable[ self.attLCSlist.currentRow() ].Name
			# Gui.Selection.addSelection('asm_Test','Model','Lego_3001.LCS_h2x1.')
			# Gui.Selection.addSelection('asm_Test','Model','LCS_0.')
			Gui.Selection.addSelection( self.activeDoc.Name, 'Model', a_Part+'.'+a_LCS+'.')
		return


	"""
    +-----------------------------------------------+
    |                     Cancel                    |
    |           restores the previous values        |
    +-----------------------------------------------+
	"""
	def onCancel(self):
		# restore previous expression if it existed
		if self.old_EE:
			self.selectedDatum.setExpression('Placement', self.old_EE )
		self.selectedDatum.recompute()
		# highlight the selected LCS in its new position
		Gui.Selection.clearSelection()
		Gui.Selection.addSelection( self.activeDoc.Name, 'Model', self.selectedDatum.Name +'.')
		self.close()


	"""
    +-----------------------------------------------+
    |                      OK                       |
    |               accept and close                |
    +-----------------------------------------------+
	"""
	def onOK(self):
		self.onApply()
		self.close()



	"""
    +-----------------------------------------------+
    |                  confirm Box                  |
    +-----------------------------------------------+
	"""
	def confirmBox(self):
		self.setWindowTitle('Please confirm')
		self.setWindowIcon( QtGui.QIcon( os.path.join( iconPath , 'FreeCad.svg' ) ) )
		self.setMinimumSize(550, 200)
		self.resize(550,240)
		self.setModal(False)
		# make this dialog stay above the others, always visible
		self.setWindowFlags( QtCore.Qt.WindowStaysOnTopHint )
		self.msgLine1 = QtGui.QLabel(self)
		self.msgLine1.move(10,20)
		self.msgLine2 = QtGui.QLabel(self)
		self.msgLine2.move(10,50)
		self.msgLine3 = QtGui.QLabel(self)
		self.msgLine3.move(10,100)
		self.msgLine1.setText( 'The selected Datum object \"'+self.selectedDatum.Name+'\"')
		self.msgLine2.setText( 'is currently mapped to geometry in the assembly.' )
		self.msgLine3.setText( 'Are you sure you want to continue ?')
		# Cancel button
		self.CancelButton = QtGui.QPushButton('Cancel', self)
		self.CancelButton.setToolTip("Quit without changes")
		self.CancelButton.setAutoDefault(False)
		self.CancelButton.move(10, 150)
		# OK button
		self.OKButton = QtGui.QPushButton('OK', self)
		self.OKButton.setToolTip("Confirm")
		self.OKButton.setAutoDefault(True)
		self.OKButton.move(460, 150)
		self.CancelButton.clicked.connect( self.onCancelConfirm )
		self.OKButton.clicked.connect( self.onOKConfirm )
		self.show()


	"""
    +-----------------------------------------------+
    |            Cancel the confirmation            |
    +-----------------------------------------------+
	"""
	def onCancelConfirm(self):
		return(False)

	"""
    +-----------------------------------------------+
    |                   OK confirm                  |
    +-----------------------------------------------+
	"""
	def onOKConfirm(self):
		return(True)


	"""
    +-----------------------------------------------+
    |     defines the UI, only static elements      |
    +-----------------------------------------------+
	"""
	def drawUI(self):
		# Our main window will be a QDialog
		self.setWindowTitle('Attach a Coordinate System')
		self.setWindowIcon( QtGui.QIcon( os.path.join( iconPath , 'FreeCad.svg' ) ) )
		self.setMinimumSize(370, 570)
		self.resize(370,570)
		self.setModal(False)
		# make this dialog stay above the others, always visible
		self.setWindowFlags( QtCore.Qt.WindowStaysOnTopHint )

		# Part, Left side
		#
		# Selected Link label
		self.lcsLabel = QtGui.QLabel(self)
		self.lcsLabel.setText("Selected Datum object :")
		self.lcsLabel.move(10,20)
		# the name as seen in the tree of the selected link
		self.lscName = QtGui.QLineEdit(self)
		self.lscName.setReadOnly(True)
		self.lscName.setText( self.selectedDatum.Name )
		self.lscName.setMinimumSize(150, 1)
		self.lscName.move(170,18)

		# combobox showing all available App::Link
		self.parentList = QtGui.QComboBox(self)
		self.parentList.move(10,80)
		self.parentList.setMinimumSize(350, 1)
		# initialize with an explanation
		self.parentList.addItem( 'Select linked Part' )

		# label
		self.parentLabel = QtGui.QLabel(self)
		self.parentLabel.setText("Linked Part :")
		self.parentLabel.move(10,120)
		# the document containing the linked object
		self.parentDoc = QtGui.QLineEdit(self)
		self.parentDoc.setReadOnly(True)
		self.parentDoc.setMinimumSize(300, 1)
		self.parentDoc.move(30,150)
		# label
		self.labelRight = QtGui.QLabel(self)
		self.labelRight.setText("Select LCS in linked Part :")
		self.labelRight.move(10,200)
		# The list of all attachment LCS in the assembly is a QListWidget
		# it is populated only when the parent combo-box is activated
		self.attLCSlist = QtGui.QListWidget(self)
		self.attLCSlist.move(10,240)
		self.attLCSlist.setMinimumSize(350, 200)

		# Expression
		#
		# expression label
		self.labelExpression = QtGui.QLabel(self)
		self.labelExpression.setText("Expression Engine :")
		self.labelExpression.move(10,450)
		# Create a line that will contain full expression for the expression engine
		self.expression = QtGui.QLineEdit(self)
		self.expression.setMinimumSize(350, 0)
		self.expression.move(10, 480)

		# Buttons
		#
		# Cancel button
		self.CancelButton = QtGui.QPushButton('Cancel', self)
		self.CancelButton.setAutoDefault(False)
		self.CancelButton.move(10, 530)

		# Apply button
		self.ApplyButton = QtGui.QPushButton('Apply', self)
		self.ApplyButton.setAutoDefault(False)
		self.ApplyButton.move(150, 530)
		self.ApplyButton.setDefault(True)

		# OK button
		self.OKButton = QtGui.QPushButton('OK', self)
		self.OKButton.setAutoDefault(False)
		self.OKButton.move(280, 530)
		self.OKButton.setDefault(True)

		# Actions
		self.CancelButton.clicked.connect(self.onCancel)
		self.ApplyButton.clicked.connect(self.onApply)
		self.OKButton.clicked.connect(self.onOK)
		self.parentList.currentIndexChanged.connect( self.onParentList )
		self.attLCSlist.itemClicked.connect( self.onDatumClicked )


	"""
    +-----------------------------------------------+
    |                 initial check                 |
    +-----------------------------------------------+
	"""
	def checkSelectionLCS(self):
		# check that there is an App::Part called 'Model'
		# a standard App::Part would also do, but then more error checks are necessary
		if not self.activeDoc.getObject('Model') or not self.activeDoc.getObject('Model').TypeId=='App::Part' :
			msgBox = QtGui.QMessageBox()
			msgBox.setWindowTitle('Warning')
			msgBox.setIcon(QtGui.QMessageBox.Critical)
			msgBox.setText("This placement is not compatible with this assembly.")
			msgBox.exec_()
			return(False)
		# check that something is selected
		if not Gui.Selection.getSelection():
			msgBox = QtGui.QMessageBox()
			msgBox.setWindowTitle('Warning')
			msgBox.setIcon(QtGui.QMessageBox.Critical)
			msgBox.setText("Please select a linked part.")
			msgBox.exec_()
			return(False)
		# set the (first) selected object as global variable
		selectedObj = Gui.Selection.getSelection()[0]
		selectedType = selectedObj.TypeId
		# check that the selected object is a Datum CS or Point type
		if not (selectedType == 'PartDesign::CoordinateSystem' or selectedType == 'PartDesign::Point'):
			msgBox = QtGui.QMessageBox()
			msgBox.setWindowTitle('Warning')
			msgBox.setIcon(QtGui.QMessageBox.Critical)
			msgBox.setText("Please select a Datum Point or Coordinate System.")
			msgBox.exec_()
			return(False)
		# now we should be safe
		return( selectedObj )



"""
    +-----------------------------------------------+
    |       add the command to the workbench        |
    +-----------------------------------------------+
"""
Gui.addCommand( 'placeDatumCmd', placeDatum() )
