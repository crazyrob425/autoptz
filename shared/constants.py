import cv2
import os

ROOT_DIR = os.path.abspath(os.curdir)
APP_DATA_DIR = os.path.expanduser('~/.autoptz/data')
MAP_LAYOUT_PATH = os.path.join(APP_DATA_DIR, 'map_layout.json')
TRAINER_PATH = ROOT_DIR + "/logic/image_processing/models/"
ENCODINGS_PATH = ROOT_DIR + '/logic/image_processing/models/encodings.pickle'
CAFFEMODEL_PATH = ROOT_DIR + \
    '/logic/image_processing/models/MobileNetSSD_deploy.caffemodel'
PROTOTXT_PATH = ROOT_DIR + \
    '/logic/image_processing/models/MobileNetSSD_deploy.prototxt'
FONT = cv2.FONT_HERSHEY_SIMPLEX
MOTION_THRESHOLD = 0.03
MOTION_HOLD_SECONDS = 2.5
CAMERA_STYLESHEET = """
                    QLabel[active="false"]{
                        border: 2.5px solid slategray;
                        border-radius: 3px;}

                    QLabel::hover {
                        border: 2.5px solid crimson;
                        border-radius: 3px;}

                    QLabel[active="true"]{
                        border: 2.5px solid dodgerblue;
                        border-radius: 3px;}
                    """
CURRENT_ACTIVE_CAM_WIDGET = None
CURRENT_ACTIVE_PTZ_DEVICE = None
ATTENDANCE_MANAGER = None
AUTO_REGISTRATION_MANAGER = None
IN_USE_USB_PTZ_DEVICES = []
ASSIGNED_USB_PTZ_CAMERA_WIDGETS = []
RUNNING_HARDWARE_CAMERA_WIDGETS = []
ICON_PNG = ROOT_DIR + '/shared/AutoPTZLogo.png'
NDI_SOURCE_LIST = []
