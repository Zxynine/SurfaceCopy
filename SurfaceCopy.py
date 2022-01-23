#Author-ZXYNINE
#Description-A tool used to copy surfaces for modification.

from __future__ import annotations
import adsk.core, adsk.fusion

import os.path as path
# Import relative path to avoid namespace pollution
from .AddinLib import utils, events, manifest, error, geometry, AppObjects,timeline,CustomGraphics
from .AddinLib.CommandInputs import CommandInputs,TransformValueInput
utils.ReImport_List(AppObjects, events, manifest, error, geometry, timeline,CustomGraphics, utils)



ADDINNAME = 'CopySurface'
VERSION = manifest.getVersion()
FILE_DIR = path.dirname(path.realpath(__file__))
VERSION_INFO = f'({ADDINNAME} v {VERSION})'
CMD_DESCRIPTION = 'A tool used to copy surfaces for modification.'
COMMAND_DATA = f'{CMD_DESCRIPTION}\n\n{VERSION_INFO}\n'

app_:adsk.core.Application = None
ui_:adsk.core.UserInterface = None
error_catcher_ = error.ErrorCatcher(True)
events_manager_ = events.EventsManager(error_catcher_)


class CommandObject:
	def __init__(self,id,cmdDef: adsk.core.CommandDefinition=None,cmdCtrl: adsk.core.CommandControl=None):
		self.id = id
		self.definition=cmdDef
		self.control=cmdCtrl
	def addDefinition(self,displayName:str,resourceFolder:str,tooltip=''):
		utils.getDelete(ui_.commandDefinitions,self.id)
		self.definition = ui_.commandDefinitions.addButtonDefinition(self.id,displayName,tooltip,resourceFolder)
	def addControl(self, parent:adsk.core.ToolbarControls,isPromoted=False,positionId='',isBefore=False):
		utils.getDelete(parent,self.id)
		self.control = parent.addCommand(self.definition,positionId,isBefore)
		if isPromoted:self.control.isPromotedByDefault = True
	def clear(self):utils.deleteAll(self.control,self.definition)

COPY_SURFACE_TOOL = CommandObject('Tion_SurfaceCopyTool')

@error_catcher_
def run(context):
	global app_, ui_
	app_,ui_ = AppObjects.GetAppUI()
	surfparent = ui_.allToolbarPanels.itemById('SurfaceModifyPanel').controls
	COPY_SURFACE_TOOL.addDefinition('Copy','./resources/CopySurface',COMMAND_DATA)
	COPY_SURFACE_TOOL.addControl(surfparent,True,'FusionMoveCommand')
	events_manager_.add_handler(COPY_SURFACE_TOOL.definition.commandCreated, CopySurfaceCommandCreated)

def stop(context):
	events_manager_.clean_up()
	COPY_SURFACE_TOOL.clear()


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SurfaceCopyInput:adsk.core.SelectionCommandInput=None
SurfaceMoveInput:TransformValueInput = None
isSelected = False

def CopySurfaceCommandCreated(args: adsk.core.CommandCreatedEventArgs):
	global SurfaceCopyInput,SurfaceMoveInput,isSelected
	inputs = CommandInputs(args.command.commandInputs)
	
	SurfaceCopyInput = inputs.addSelectionInput('SurfaceSelect', 'Surfaces To Copy:','Select all faces/surfaces you wish to copy.')
	SurfaceCopyInput.selectionFilters = ['Faces']
	SurfaceCopyInput.setSelectionLimits(1,0)

	SurfaceMoveInput = inputs.addMoveCommandInput('MoveSurfaces', 'Move Handle')
	isSelected=SurfaceMoveInput.isEnabled = False

	args.command.isExecutedWhenPreEmpted = False
	events_manager_.add_handler(args.command.inputChanged,CopySurfaceInputChanged)
	events_manager_.add_handler(args.command.executePreview,CopySurfacePreview)
	events_manager_.add_handler(args.command.execute,CopySurfaceExecute)

def CopySurfaceInputChanged(args:adsk.core.InputChangedEventArgs):
	global isSelected
	if SurfaceCopyInput.selectionCount <= 0:
		isSelected=SurfaceMoveInput.isEnabled=False
	elif not isSelected:
		SurfaceMoveInput.setLocation(SurfaceCopyInput.selection(0).point)
		isSelected=SurfaceMoveInput.isEnabled=True


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def getExecuteObjs():
	selectedObjs:list[adsk.fusion.BRepBody] = [sel.entity for sel in utils.Items.custom(SurfaceCopyInput.selection,SurfaceCopyInput.selectionCount)]
	distVec = SurfaceMoveInput.DistanceVector()
	root = AppObjects.GetRoot()
	return selectedObjs,distVec,root


def CopySurfacePreview(args:adsk.core.CommandEventArgs):
	if SurfaceCopyInput.selectionCount <= 0:return
	selectedObjs,distVec,root = getExecuteObjs()

	GRAPHICS = CustomGraphics.ClearCustomGraphics(root,True)
	for body in selectedObjs:
		BodyGroup = CustomGraphics.MeshFromBRep(GRAPHICS,body)
		if distVec.length == 0:continue
		else: translation = geometry.Matrix.translation(distVec,BodyGroup.transform)
		BodyGroup.transform = translation


def CopySurfaceExecute(args:adsk.core.CommandEventArgs):
	if SurfaceCopyInput.selectionCount <= 0:return
	selectedObjs,distVec,root = getExecuteObjs()
	offsetFaceFeatures = root.features.offsetFeatures
	moveFeatures = root.features.moveFeatures

	if distVec.length == 0:translation = None
	else: translation = geometry.Matrix.translation(distVec)
	with timeline.GroupManager('Surface Copy'):
		for body in selectedObjs:
			copyInput = offsetFaceFeatures.createInput(utils.Collections.single(body), adsk.core.ValueInput.createByReal(0.0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation,False)
			offsetFaceFeature:adsk.fusion.OffsetFeature = offsetFaceFeatures.add(copyInput)
			if translation is not None:		
				moveInput = moveFeatures.createInput(utils.Collections.fromIterable(offsetFaceFeature.bodies), translation)
				moveFeatures.add(moveInput)
