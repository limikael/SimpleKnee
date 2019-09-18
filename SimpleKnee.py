from submodule.modwb import icon
from submodule.pytriangle.Triangle import Triangle
from PySide.QtCore import Slot, QTimer, QObject
import FreeCAD, math
__icon__="res/SimpleKnees.svg"

class Timer(QObject):
	onTimer=None

	def __init__(self, interval):
		super(Timer, self).__init__()
		self.timer = QTimer(self)
		self.timer.timeout.connect(self.handleTimer)
		self.timer.start(interval)

	def stop(self):
		self.timer.stop()

	@Slot()
	def handleTimer(self):
		if self.onTimer:
			self.onTimer()

def _approachAngle(current, target, step):
	current%=360
	target%=360
	diff=target-current
	if diff>180:
		diff-=360
	if diff<-180:
		diff+=360
	if diff>step:
		return (current+step)%360
	if diff<-step:
		return (current-step)%360
	return target

def _getGlobalPosition(o):
	if isinstance(o,str):
		o=FreeCAD.ActiveDocument.getObjectsByLabel(o)[0]
	m=o.Placement.toMatrix()
	while len(o.InList)>=1:
		parent=o.InList[0]
		m=parent.Placement.toMatrix().multiply(m)
		o=parent
	return FreeCAD.Placement(m).Base

def _objectDistance(o1,o2):
	p1=_getGlobalPosition(o1)
	p2=_getGlobalPosition(o2)
	return math.sqrt((p2.x-p1.x)**2+(p2.y-p1.y)**2+(p2.z-p1.z)**2)

def _triangleFromObjects(o1, o2, o3):
	return Triangle([
		_objectDistance(o2,o3),
		_objectDistance(o3,o1),
		_objectDistance(o1,o2)
	])

def _setObjectRot(o,angle):
	if isinstance(o,str):
		o=FreeCAD.ActiveDocument.getObjectsByLabel(o)[0]
	o.Placement.Rotation.Angle=math.radians(angle)

def _getObjectRot(o):
	if isinstance(o,str):
		o=FreeCAD.ActiveDocument.getObjectsByLabel(o)[0]
	return math.degrees(o.Placement.Rotation.Angle)

def _objectAngles(oo,o1,o2,debug=False):
	po=_getGlobalPosition(oo)
	p1=_getGlobalPosition(o1)
	p2=_getGlobalPosition(o2)
	u=po.sub(p1)
	v=po.sub(p2)
	a=math.degrees(u.getAngle(v))

	if oo.Placement.Rotation.Axis.dot(v.cross(u))<0:
		return 360-a

	return a

def _calculateKnee(hipPart,kneePart,tipPart,targetPart,step=180):
	hipCurrent=_getObjectRot(hipPart)
	kneeCurrent=_getObjectRot(kneePart)

	_setObjectRot(kneePart,0)
	_setObjectRot(hipPart,0)

	defaultHipAngle=_objectAngles(hipPart,kneePart,targetPart)
	defaultKneeAngle=_objectAngles(kneePart,tipPart,hipPart)

	targetTriangle=Triangle([
		_objectDistance(kneePart,tipPart),
		_objectDistance(hipPart,targetPart),
		_objectDistance(hipPart,kneePart)
	])

	hipTarget=targetTriangle.get_degree(0)-defaultHipAngle
	if hipPart.Placement.Rotation.Axis.dot(kneePart.Placement.Rotation.Axis)<0:
		kneeTarget=180-(targetTriangle.get_degree(1)-defaultKneeAngle)
	else:
		kneeTarget=targetTriangle.get_degree(1)-defaultKneeAngle

	_setObjectRot(hipPart,_approachAngle(hipCurrent,hipTarget,step))
	_setObjectRot(kneePart,_approachAngle(kneeCurrent,kneeTarget,step))

def _getChildPartByType(parent, childType):
	for o in parent.OutList:
		if o.TypeId=="App::Part" and o.Type==childType:
			return o

	raise Exception(parent.Label+" should have a "+childType)

def _calculateKnees(step=180):
	doc=FreeCAD.ActiveDocument
	for o in doc.Objects:
		if o.TypeId=="App::Part" and o.Type=="Hip":
			hipPart=o
			kneePart=_getChildPartByType(hipPart,"Knee")
			tipPart=_getChildPartByType(kneePart,"Tip")

			a=doc.getObjectsByLabel(tipPart.Id)
			if len(a)<1:
				raise Exception("Designated target "+tipPart.Id+" not found")

			targetPart=a[0]
			_calculateKnee(hipPart,kneePart,tipPart,targetPart,step)

def _resetKnees():
	doc=FreeCAD.ActiveDocument
	for o in doc.Objects:
		if (o.TypeId=="App::Part"
				and (o.Type=="Hip" or o.Type=="Knee")):
			o.Placement.Rotation.Angle=0

def _calcTimer():
	_calculateKnees(1)

@icon("res/CalculateKnees.svg")
def CalculateKnees():
	StopKneeSimulation()
	_calculateKnees()

@icon("res/ResetKnees.svg")
def ResetKnees():
	StopKneeSimulation()
	_resetKnees()

@icon("res/StartKneeSimulation.svg")
def StartKneeSimulation():
	StopKneeSimulation()
	FreeCAD.kneeTimer=Timer(50)
	FreeCAD.kneeTimer.onTimer=_calcTimer

@icon("res/StopKneeSimulation.svg")
def StopKneeSimulation():
	if "kneeTimer" in FreeCAD.__dict__:
		FreeCAD.kneeTimer.stop()
		del FreeCAD.kneeTimer