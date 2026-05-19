import os
import pickle
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QDialog, QFileDialog, QListWidget, QLabel
from shared import constants
from shared.message_prompts import show_info_messagebox


class AddFaceUI(object):
    """
    Creation for Add Face UI
    """

    def __init__(self):
        self.name_line = None
        self.photo_list = None
        self.photo_hint_label = None
        self.selected_files = []
        self.horizontalLayout = None
        self.cancel_btn = None
        self.enter_name_btn = None
        self.choose_photos_btn = None
        self.camera = None
        self.add_face_title_label = None
        self.verticalLayout = None
        self.window = None
        self.count = 0

    def setupUi(self, add_face, camera):
        """
        Used for setup when calling the AddFaceDlg Class
        :param add_face:
        :param camera:
        """
        self.window = add_face
        self.camera = camera
        add_face.setObjectName("add_face")
        add_face.resize(440, 340)
        self.verticalLayout = QtWidgets.QVBoxLayout(add_face)
        self.verticalLayout.setObjectName("verticalLayout")
        self.add_face_title_label = QtWidgets.QLabel(add_face)
        self.add_face_title_label.setText("add_face_title")
        self.verticalLayout.addWidget(self.add_face_title_label)

        self.name_line = QtWidgets.QLineEdit(add_face)
        self.name_line.setObjectName("name_line")
        self.verticalLayout.addWidget(self.name_line)

        self.photo_hint_label = QLabel(add_face)
        self.photo_hint_label.setWordWrap(True)
        self.photo_hint_label.setText(
            "Optional: choose multiple face photos for faster enrollment, or skip this and use the live camera capture flow."
        )
        self.verticalLayout.addWidget(self.photo_hint_label)

        self.choose_photos_btn = QtWidgets.QPushButton(add_face)
        self.choose_photos_btn.setObjectName("choose_photos_btn")
        self.choose_photos_btn.clicked.connect(self.choose_photos)
        self.verticalLayout.addWidget(self.choose_photos_btn)

        self.photo_list = QListWidget(add_face)
        self.photo_list.setObjectName("photo_list")
        self.verticalLayout.addWidget(self.photo_list)

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.enter_name_btn = QtWidgets.QPushButton(add_face)
        self.enter_name_btn.setObjectName("enter_name_btn")
        self.enter_name_btn.clicked.connect(self.add_face_prompt)
        self.horizontalLayout.addWidget(self.enter_name_btn)

        self.cancel_btn = QtWidgets.QPushButton(add_face)
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.window.close)
        self.horizontalLayout.addWidget(self.cancel_btn)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.translate_ui(add_face)
        QtCore.QMetaObject.connectSlotsByName(add_face)

    def choose_photos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self.window,
            "Select face photos",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if files:
            self.selected_files = files
            self.photo_list.clear()
            for path in files:
                self.photo_list.addItem(path)

    def add_face_prompt(self):
        """
        Methods that checks what the user inputs in the dialog.
        If the name already exists then add face to the existing database.
        Set the current active CameraWidget's add_name variable to start detecting and saving images with a person.
        :return:
        """
        if self.name_line.text().strip() == "":
            return
        else:
            print("Adding Face with " + self.camera.objectName())
            person_name = self.name_line.text().strip()
            # check if encodings file and face exists, if not add to encodings file
            if os.path.exists(constants.ENCODINGS_PATH):
                print("loading encoded model")
                encodings = pickle.loads(open(constants.ENCODINGS_PATH, "rb").read())
                known_face_encodings = encodings

                if person_name in set(known_face_encodings['names']):
                    print("\n [INFO] Name in Database")
                    show_info_messagebox(
                        "User's Face Already Exists.\nAdding new look to existing user.")
            else:
                show_info_messagebox(
                    "Initializing face capture. \nLook at the selected camera and wait, or use the photo picker for multi-image enrollment.")
                print(
                    "\n [INFO] Initializing face capture. Look at the select camera and wait...")

            if self.selected_files:
                added = self.camera.facial_recognition.add_faces_from_images(person_name, self.selected_files)
                if added:
                    show_info_messagebox(f"Added {added} photo sample(s) for {person_name}.")
                else:
                    show_info_messagebox("No usable face found in the selected photos.")
            else:
                self.camera.facial_recognition.set_add_face_name(name=person_name)
            self.window.close()

    def translate_ui(self, add_face):
        """
        Automatic Translation Locale
        :param add_face:
        """
        _translate = QtCore.QCoreApplication.translate
        add_face.setWindowTitle(_translate("add_face", "Add Face"))
        self.add_face_title_label.setText(
            _translate("add_face_title", "Enter Name and optionally add multiple photos:"))
        self.choose_photos_btn.setText(_translate("choose_photos_btn", "Choose Photos..."))
        self.enter_name_btn.setText(_translate("enter_name_btn", "Submit"))
        self.cancel_btn.setText(_translate("cancel_btn", "Cancel"))


class AddFaceDlg(QDialog):
    """Run Add Face Dialog"""

    def __init__(self, parent=None, camera=None):
        super().__init__(parent)
        # Create an instance of the GUI
        self.ui = AddFaceUI()
        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self, camera=camera)
