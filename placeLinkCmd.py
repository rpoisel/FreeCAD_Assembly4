#!/usr/bin/env python3
# coding: utf-8
#
# placeLinkCmd.py


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
class placeLink( QtGui.QDialog ):
	"My tool object"


	def __init__(self):
		super(placeLink,self).__init__()
		self.selectedLink = []
		self.attLCStable = []


	def GetResources(self):
		return {"MenuText": "Edit Placement of a linked Part",
				"ToolTip": "Move an instance of an external Part",
				"Pixmap" : os.path.join( iconPath , 'Place_Link.svg')
				}


	def IsActive(self):
		# is there an active document ?
		if App.ActiveDocument:
			# is something selected ?
			if Gui.Selection.getSelection():
				if Gui.Selection.getSelection()[0].isDerivedFrom('App::Link'):
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

		# check that we have selected an App::Link object
		selection = self.checkSelection()
		if not selection:
			self.close()
		else:
			self.selectedLink = selection


		# draw the GUI, objects are defined later down
		self.drawUI()


		# the parent (top-level) assembly is the App::Part called Model (hard-coded)
		# What would happen if there are 2 App::Part ?
		self.parentAssembly = self.activeDoc.Model
		# Initialize the assembly tree with the Parrent Assembly as first element
		# all the parts in the assembly, except the selected link
		self.asmParts = []
		# the first item is "Select attachment Parent" therefore we add an empty object
		self.asmParts.append( [] )
		self.asmParts.append( self.parentAssembly )
		# Add it as first element to the drop-down combo-box
		parentIcon = self.parentAssembly.ViewObject.Icon
		self.parentList.addItem( parentIcon, 'Parent Assembly', self.parentAssembly )

		# find all the linked parts in the assembly
		for obj in self.activeDoc.findObjects("App::Link"):
			# add it to our list if it's a link to an App::Part ...
			if obj.LinkedObject.isDerivedFrom('App::Part'):
				# ... except if it's the selected link itself
				if obj != self.selectedLink:
					self.asmParts.append( obj )
					# add to the drop-down combo box with the assembly tree's parts
					objIcon = obj.LinkedObject.ViewObject.Icon
					self.parentList.addItem( objIcon, obj.Name, obj)


		# find all the LCS in the selected link
		self.partLCStable = self.getPartLCS( self.selectedLink.LinkedObject )
		# build the list
		for lcs in self.partLCStable:
			newItem = QtGui.QListWidgetItem()
			if lcs.Name == lcs.Label:
				newItem.setText( lcs.Name )
			else:
				newItem.setText( lcs.Label + ' (' +lcs.Name+ ')' )
			#newItem.setIcon( lcs.ViewObject.Icon )
			#self.lcsIcon = lcs.ViewObject.Icon
			self.partLCSlist.addItem(newItem)


		self.old_AO = []
		self.constrFeature = []
		self.old_Parent = ''
		# name of the constraints object for the link
		self.constrName = constraintPrefix + self.selectedLink.Name
		# check whether it exists
		constraint = self.activeDoc.getObject('Constraints').getObject( self.constrName )
		if constraint:
			self.constrFeature = constraint
			# get and store the current AttachmentOffset
			self.old_AO = self.constrFeature.AttachmentOffset
			# get and store the current attachment parent
			self.old_Parent = self.constrFeature.AttachedTo

		self.old_EE = ''
		# get and store the current expression engine:
		old_EE = self.selectedLink.ExpressionEngine
		if old_EE:
			( pla, self.old_EE ) = old_EE[0]

		# for debugging, use this field to print text
		#self.expression.setText( self.old_attPart )


		# decode the old ExpressionEngine
		old_Parent = ''
		old_ParentPart = ''
		old_attLCS = ''
		constrName = ''
		linkedPart = ''
		old_linkLCS = ''
		# if the decode is unsuccessful, old_Expression is set to False and the other things are set to 'None'
		( old_Parent, old_ParentPart, old_attLCS, constrName, linkedPart, old_linkLCS ) = splitExpressionPart( self.old_EE, self.old_Parent )


		# find the old LCS in the list of LCS of the linked part...
		# MatchExactly, MatchContains, MatchEndsWith ...
		lcs_found = []
		lcs_found = self.partLCSlist.findItems( old_linkLCS, QtCore.Qt.MatchExactly )
		if lcs_found:
			# ... and select it
			self.partLCSlist.setCurrentItem( lcs_found[0] )
		else:
			# may-be it was renamed, see if we can find it as (name)
			lcs_found = self.partLCSlist.findItems( '('+old_linkLCS+')', QtCore.Qt.MatchContains )
			if lcs_found:
				self.partLCSlist.setCurrentItem( lcs_found[0] )


		# find the oldPart in the part list...
		oldPart = self.parentList.findText( old_Parent )
		# if not found
		if oldPart == -1:
			self.parentList.setCurrentIndex( 0 )
		else:
			self.parentList.setCurrentIndex( oldPart )
			# this should have triggered self.getPartLCS() to fill the LCS list


		# find the oldLCS in the old parent Part (actually the App::Link)...
		#self.oldLCS = self.attLCSlist.findItems( self.old_attLCS, QtCore.Qt.CaseSensitive )
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


		# the widget is shown and not executed to allow it to stay on top
		self.show()



	"""
    +-----------------------------------------------+
    |           create the constr_LinkName          |
    |            for the App::Link object           |
    +-----------------------------------------------+
	"""
	def makeConstrFeature( self ):
		# get the name of the App::Link
		linkName = self.selectedLink.Name
		# the name of the constraint:
		constrName = constraintPrefix + linkName
		# if it exists, return the existing constrFeature
		# TODO : check that it's of the correct type ?
		if self.activeDoc.getObject('Constraints').getObject( constrName ):
			return self.activeDoc.getObject('Constraints').getObject( constrName )
		# if it didn't exist, create it ...
		constrFeature = self.activeDoc.getObject('Constraints').newObject( 'App::FeaturePython', constrName )
		#self.expression.setText( constrName +' does not exist, creating' )
		#self.expression.setText( constrName +' has been created' )
		# ...and create the property fields
		#
		# Store the type of solver to use
		constrFeature.addProperty( 'App::PropertyString', 'Solver' )
		constrFeature.Solver = 'ExpressionEngine'
		# Store the type of the constraint
		constrFeature.addProperty( 'App::PropertyString', 'ConstraintType' )
		constrFeature.ConstraintType = 'AttachmentByLCS'
		# Enabled ?
		constrFeature.addProperty( 'App::PropertyBool', 'Enabled' )
		constrFeature.Enabled = True
		# store the name of the inserted Part's instance
		constrFeature.addProperty( 'App::PropertyString', 'Instance', 'Attachment' )
		constrFeature.Instance = linkName
		# store the name of the LCS in the assembly where the link is attached to
		constrFeature.addProperty( 'App::PropertyString', 'AttachedByLCS', 'Attachment' )
		# store the name of the part where the link is attached to
		constrFeature.addProperty( 'App::PropertyString', 'AttachedTo', 'Attachment' )
		# store the name of the LCS in the assembly where the link is attached to
		constrFeature.addProperty( 'App::PropertyString', 'AttachedToLCS', 'Attachment' )
		# add an App::Placement that will be the offset between attachment and link LCS
		constrFeature.addProperty( 'App::PropertyPlacement', 'AttachmentOffset', 'Attachment' )
		# store the name of the App::Link this constraint refers-to
		constrFeature.addProperty( 'App::PropertyString', 'LinkName', 'Information' )
		constrFeature.LinkName = linkName
		# store the name of the linked document (only for information)
		constrFeature.addProperty( 'App::PropertyString', 'LinkedPart', 'Information' )
		constrFeature.LinkedPart = self.selectedLink.LinkedObject.Document.Name
		# store the name of the linked file (only for information)
		constrFeature.addProperty( 'App::PropertyString', 'LinkedFile', 'Information' )
		constrFeature.LinkedFile = self.selectedLink.LinkedObject.Document.FileName
		# return
		return constrFeature



	"""
    +-----------------------------------------------+
    | check that all necessary things are selected, |
    |   populate the expression with the selected   |
    |    elements, put them into the constraint     |
    |   and trigger the recomputation of the part   |
    +-----------------------------------------------+
	"""
	def onApply( self ):
		# get the instance to attach to:
		# it's either the top level assembly or a sister App::Link
		if self.parentList.currentText() == 'Parent Assembly':
			a_Link = 'Parent Assembly'
			a_Part = None
		elif self.parentList.currentIndex() > 1:
			parent = self.asmParts[ self.parentList.currentIndex() ]
			a_Link = parent.Name
			a_Part = parent.LinkedObject.Document.Name
		else:
			a_Link = None
			a_Part = None


		# the attachment LCS's name in the parent
		# check that something is selected in the QlistWidget
		if self.attLCSlist.selectedItems():
			#a_LCS = self.attLCSlist.selectedItems()[0].text()
			a_LCS = self.attLCStable[ self.attLCSlist.currentRow() ].Name
		else:
			a_LCS = None


		# the linked App::Part's name
		l_Part = self.selectedLink.LinkedObject.Document.Name
		# the constraint's name:
		c_Name = self.constrName

		# the LCS's name in the linked part to be used for its attachment
		# check that something is selected in the QlistWidget
		if self.partLCSlist.selectedItems():
			#l_LCS = self.partLCSlist.selectedItems()[0].text()
			l_LCS = self.partLCStable[ self.partLCSlist.currentRow() ].Name
		else:
			l_LCS = None
		#self.expression.setText( '***'+ l_LCS +'***' )

		# check that all of them have something in
		# constrName has been checked at the beginning
		if not ( a_Link and a_LCS and c_Name and l_Part and l_LCS ) :
			self.expression.setText( 'Problem in selections' )
		else:
			# this is where all the magic is, see:
			# 
			# https://forum.freecadweb.org/viewtopic.php?p=278124#p278124
			#
			# as of FreeCAD v0.19 the syntax is different:
			# https://forum.freecadweb.org/viewtopic.php?f=17&t=38974&p=337784#p337784
			#
			# expr = ParentLink.Placement * ParentPart#LCS.Placement * constr_LinkName.AttachmentOffset * LinkedPart#LCS.Placement ^ -1'			
			# expr = LCS_in_the_assembly.Placement * constr_LinkName.AttachmentOffset * LinkedPart#LCS.Placement ^ -1'			
			expr = makeExpressionPart( a_Link, a_Part, a_LCS, c_Name, l_Part, l_LCS )
			# this can be skipped when this method becomes stable
			self.expression.setText( expr )
			# fill the constraint feature. Create it if it doesn't exist:
			self.constrFeature = self.makeConstrFeature()
			# store the part where we're attached to in the constraints object
			self.constrFeature.AttachedByLCS = '#'+l_LCS
			self.constrFeature.AttachedTo = a_Link
			self.constrFeature.AttachedToLCS = '#'+a_LCS
			# load the expression into the link's Expression Engine
			self.selectedLink.setExpression('Placement', expr )
			# recompute the object to apply the placement:
			self.selectedLink.recompute()
		return



	"""
    +-----------------------------------------------+
    |   find all the linked parts in the assembly   |
    +-----------------------------------------------+
	"""
	def getAllLinkedParts(self):
		allLinkedParts = []
		for obj in self.activeDoc.findObjects("App::Link"):
			# add it to our list if it's a link to an App::Part ...
			if obj.LinkedObject.isDerivedFrom('App::Part'):
				# ... except if it's the selected link itself, because
				# we don't want to place the new link relative to itself !
				if obj != self.selectedLink:
					allLinkedParts.append( obj )
		return allLinkedParts



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
			if obj.TypeId == 'PartDesign::CoordinateSystem':
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
		# partLCS = []
		# ... or it's 'Parent Assembly' then the parent is the 'Model' root App::Part
		if parentName =='Parent Assembly':
			parentPart = self.activeDoc.getObject( 'Model' )
			# we get the LCS directly in the root App::Part 'Model'
			self.attLCStable = self.getPartLCS( parentPart )
			self.parentDoc.setText( parentPart.Document.Name )
		# a sister object is an App::Link
		# the .LinkedObject is an App::Part
		else:
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
			if lcs.Name == lcs.Label:
				newItem.setText( lcs.Name )
			else:
				newItem.setText( lcs.Label + ' (' +lcs.Name+ ')' )
			newItem.setIcon( lcs.ViewObject.Icon )
			self.attLCSlist.addItem( newItem )
			#self.attLCStable.append(lcs)
		return



	"""
    +-----------------------------------------------+
    |  An LCS has been clicked in 1 of the 2 lists  |
    |              We highlight both LCS            |
    +-----------------------------------------------+
	"""
	def onLCSclicked( self ):
		# clear the selection in the GUI window
		Gui.Selection.clearSelection()
		# LCS of the linked part
		if self.partLCSlist.selectedItems():
			#p_LCS = self.partLCSlist.selectedItems()[0].text()
			p_LCS = self.partLCStable[ self.partLCSlist.currentRow() ].Name
			Gui.Selection.addSelection( self.activeDoc.Name, 'Model', self.selectedLink.Name+'.'+p_LCS+'.')
		# LCS in the parent
		if self.attLCSlist.selectedItems():
			#a_LCS = self.attLCSlist.selectedItems()[0].text()
			a_LCS = self.attLCStable[ self.attLCSlist.currentRow() ].Name
			# get the part where the selected LCS is
			a_Part = self.parentList.currentText()
			# parent assembly and sister part need a different treatment
			if a_Part == 'Parent Assembly':
				linkDot = ''
			else:
				linkDot = a_Part+'.'
			Gui.Selection.addSelection( self.activeDoc.Name, 'Model', linkDot+a_LCS+'.')
		return



	"""
    +-----------------------------------------------+
    |                     Cancel                    |
    |           restores the previous values        |
    +-----------------------------------------------+
	"""
	def onCancel(self):
		# restore previous values
		if self.old_AO:
			self.constrFeature.AttachmentOffset = self.old_AO
		if self.old_EE:
			self.selectedLink.setExpression( 'Placement', self.old_EE )
		self.selectedLink.recompute()
		self.close()



	"""
    +-----------------------------------------------+
    |                  Rotations                    |
    +-----------------------------------------------+
	"""
	def rotAxis( self, plaRotAxis ):
		constrAO = self.constrFeature.AttachmentOffset
		self.constrFeature.AttachmentOffset = plaRotAxis.multiply( constrAO )
		self.selectedLink.recompute()
		return

	def onRotX(self):
		rotX = App.Placement( App.Vector(0,0,0), App.Rotation( App.Vector(1,0,0), 90. ) )
		self.rotAxis(rotX)
		return

	def onRotY(self):
		rotY = App.Placement( App.Vector(0,0,0), App.Rotation( App.Vector(0,1,0), 90. ) )
		self.rotAxis(rotY)
		return

	def onRotZ(self):
		rotZ = App.Placement( App.Vector(0,0,0), App.Rotation( App.Vector(0,0,1), 90. ) )
		self.rotAxis(rotZ)
		return



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
    |     defines the UI, only static elements      |
    +-----------------------------------------------+
	"""
	def drawUI(self):
		# Our main window will be a QDialog
		self.setWindowTitle('Place linked Part')
		self.setWindowIcon( QtGui.QIcon( os.path.join( iconPath , 'FreeCad.svg' ) ) )
		self.setMinimumSize(550, 640)
		self.resize(550,640)
		self.setModal(False)
		# make this dialog stay above the others, always visible
		self.setWindowFlags( QtCore.Qt.WindowStaysOnTopHint )

		# Part, Left side
		#
		# Selected Link label
		self.linkLabel = QtGui.QLabel(self)
		self.linkLabel.setText("Selected Link :")
		self.linkLabel.move(10,20)
		# the name as seen in the tree of the selected link
		self.linkName = QtGui.QLineEdit(self)
		self.linkName.setReadOnly(True)
		self.linkName.setText( self.selectedLink.Name )
		self.linkName.setMinimumSize(200, 1)
		self.linkName.move(35,50)

		# label
		self.linkedLabel = QtGui.QLabel(self)
		self.linkedLabel.setText("Linked Document :")
		self.linkedLabel.move(10,90)
		# the document containing the linked object
		self.linkedDoc = QtGui.QLineEdit(self)
		self.linkedDoc.setReadOnly(True)
		self.linkedDoc.setText( self.selectedLink.LinkedObject.Document.Name )
		self.linkedDoc.setMinimumSize(200, 1)
		self.linkedDoc.move(35,120)

		# label
		self.labelLeft = QtGui.QLabel(self)
		self.labelLeft.setText("Select LCS in Part :")
		self.labelLeft.move(10,160)
		# The list of all LCS in the part is a QListWidget
		self.partLCSlist = QtGui.QListWidget(self)
		self.partLCSlist.move(10,190)
		self.partLCSlist.setMinimumSize(100, 250)
		self.partLCSlist.setToolTip('Select a coordinate system from the list')

		# Assembly, Right side
		#
		# label
		self.slectedLabel = QtGui.QLabel(self)
		self.slectedLabel.setText("Select Part to attach to:")
		self.slectedLabel.move(280,20)
		# combobox showing all available App::Link
		self.parentList = QtGui.QComboBox(self)
		self.parentList.move(280,50)
		self.parentList.setMinimumSize(250, 1)
		self.parentList.setToolTip('Choose the part in which the attachment\ncoordinate system is to be found')
		# the parent assembly is hardcoded, and made the first real element
		self.parentList.addItem('Select attachment Parent')

		# label
		self.parentLabel = QtGui.QLabel(self)
		self.parentLabel.setText("Parent Document :")
		self.parentLabel.move(280,90)
		# the document containing the linked object
		self.parentDoc = QtGui.QLineEdit(self)
		self.parentDoc.setReadOnly(True)
		self.parentDoc.setMinimumSize(200, 1)
		self.parentDoc.move(305,120)
		# label
		self.labelRight = QtGui.QLabel(self)
		self.labelRight.setText("Select LCS in Parent :")
		self.labelRight.move(280,160)
		# The list of all attachment LCS in the assembly is a QListWidget
		# it is populated only when the parent combo-box is activated
		self.attLCSlist = QtGui.QListWidget(self)
		self.attLCSlist.move(280,190)
		self.attLCSlist.setMinimumSize(250, 250)
		self.attLCSlist.setToolTip('Select a coordinate system from the list')

		# Expression
		#
		# expression label
		self.labelExpression = QtGui.QLabel(self)
		self.labelExpression.setText("Expression Engine :")
		self.labelExpression.move(10,450)
		# Create a line that will contain full expression for the expression engine
		self.expression = QtGui.QLineEdit(self)
		self.expression.setMinimumSize(530, 0)
		self.expression.move(10, 480)

		# Buttons
		#
		# RotX button
		self.RotXButton = QtGui.QPushButton('Rot X', self)
		self.RotXButton.setToolTip("Rotate the instance around the X axis by 90deg")
		self.RotXButton.setAutoDefault(False)
		self.RotXButton.move(130, 530)
		# RotY button
		self.RotYButton = QtGui.QPushButton('Rot Y', self)
		self.RotYButton.setToolTip("Rotate the instance around the Y axis by 90deg")
		self.RotYButton.setAutoDefault(False)
		self.RotYButton.move(230, 530)
		# RotZ button
		self.RotZButton = QtGui.QPushButton('Rot Z', self)
		self.RotZButton.setToolTip("Rotate the instance around the Z axis by 90deg")
		self.RotZButton.setAutoDefault(False)
		self.RotZButton.move(330, 530)

		# Cancel button
		self.CancelButton = QtGui.QPushButton('Cancel', self)
		self.CancelButton.setToolTip("Restore initial parameters and close dialog")
		self.CancelButton.setAutoDefault(False)
		self.CancelButton.move(10, 600)
		# Apply button
		self.ApplyButton = QtGui.QPushButton('Show', self)
		self.ApplyButton.setToolTip("Previsualise the instance's placement \nwith the chosen parameters")
		self.ApplyButton.setAutoDefault(False)
		self.ApplyButton.move(230, 600)
		self.ApplyButton.setDefault(True)
		# OK button
		self.OKButton = QtGui.QPushButton('OK', self)
		self.OKButton.setToolTip("Apply current parameters and close dialog")
		self.OKButton.setAutoDefault(False)
		self.OKButton.move(460, 600)

		# Actions
		self.parentList.currentIndexChanged.connect( self.onParentList )
		#self.attLCSlist.itemClicked.connect( self.onLCSclicked )
		#self.partLCSlist.itemClicked.connect( self.onLCSclicked )
		self.RotXButton.clicked.connect( self.onRotX )
		self.RotYButton.clicked.connect( self.onRotY )
		self.RotZButton.clicked.connect( self.onRotZ)
		self.CancelButton.clicked.connect(self.onCancel)
		self.ApplyButton.clicked.connect(self.onApply)
		self.OKButton.clicked.connect(self.onOK)



	"""
    +-----------------------------------------------+
    |                 initial check                 |
    +-----------------------------------------------+
	"""
	def checkSelection(self):
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
		# we take the first of the selected object(s)
		selectedObj = Gui.Selection.getSelection()[0]
		# check that the selected object is of App::Link type
		if not selectedObj.isDerivedFrom('App::Link'):
			msgBox = QtGui.QMessageBox()
			msgBox.setWindowTitle('Warning')
			msgBox.setIcon(QtGui.QMessageBox.Critical)
			msgBox.setText("Please select a linked part.")
			msgBox.exec_()
			return(False)
		# check that there is indeed a constraint thing there
		#constraint = constraintPrefix + selectedObj.Name
		# should we also check that's it's really an App::FeaturPython type ?
		#if not self.activeDoc.getObject( constraint ):
		#	msgBox = QtGui.QMessageBox()
		#	msgBox.setWindowTitle('Warning')
		#	msgBox.setIcon(QtGui.QMessageBox.Critical)
		#	msgBox.setText("There is no constraint for this linked object.")
		#	msgBox.exec_()
		#	return( selectedObj )
		# now we should be safe
		return( selectedObj )



"""
    +-----------------------------------------------+
    |       add the command to the workbench        |
    +-----------------------------------------------+
"""
Gui.addCommand( 'placeLinkCmd', placeLink() )
