#!/usr/bin/env python3
# coding: utf-8
# 
# newBodyCmd.py 


from PySide import QtGui, QtCore
import FreeCADGui as Gui
import FreeCAD as App
import Part, math, re

from libAsm4 import *



class newBody:
	"My tool object"

	def GetResources(self):
		return {"MenuText": "New Body",
				"Accel": "Ctrl+B",
				"ToolTip": "Create a new Body in a Part",
				"Pixmap" : os.path.join( iconPath , 'Asm4_Body.svg')
				}


	def IsActive(self):
		if App.ActiveDocument:
			# is something selected ?
			if Gui.Selection.getSelection():
				# This command adds a new Sketch only to App::Part objects ...
				if Gui.Selection.getSelection()[0].TypeId == ('App::Part'):
					return(True)
				else:
					return(False)
			# ... or if there is a Model object in the active document:
			elif App.ActiveDocument.getObject('Model'):
				return(True)
			# 
			else:
				return(False)
		else:
			return(False)


	def Activated(self):
		# check that we have somewhere to put our stuff
		partChecked = self.checkPart()
		bodyName = 'Body'
		if partChecked:
			# input dialog to ask the user the name of the Sketch:
			text,ok = QtGui.QInputDialog.getText(None,'Create new Body','Enter new Body name :                                        ', text = bodyName)
			if ok and text:
				partChecked.newObject( 'PartDesign::Body', text )


	def checkPart(self):
		# if something is selected ...
		if Gui.Selection.getSelection():
			selectedObj = Gui.Selection.getSelection()[0]
			# ... and it's an App::Part:
			if selectedObj.TypeId == 'App::Part':
				return(selectedObj)
		# or of nothing is selected ...
		if App.ActiveDocument.getObject('Model'):
			# ... but there is a Model:
			return App.ActiveDocument.getObject('Model')
		else:
			return(False)


# add the command to the workbench
Gui.addCommand( 'newBodyCmd', newBody() )
