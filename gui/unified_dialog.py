"""Unified FreeCAD dialog for a single sprocket or a complete chain drive."""

from __future__ import annotations

from pathlib import Path

try:
    from PySide import QtCore, QtWidgets
except ImportError:  # Compatibility with older FreeCAD/PySide builds.
    from PySide import QtCore, QtGui

    QtWidgets = QtGui

from core.catalog import get_chain_data, load_catalog
from core.discrete_solver import calculate_discrete_chain_drive_geometry, format_result_report
from core.sprocket_catalog import (
    get_available_asa_sizes,
    get_available_teeth,
    get_sprocket,
    load_enco_sprocket_catalog,
)
from cad.asme_sprocket_generator import (
    ASME_SINGLE_FLANGE_WIDTH_MM,
    calculate_asme_tooth_geometry,
)
from cad.sprocket_library import open_or_create_sprocket_document
from config import get_legacy_library_dirs, get_output_dir, get_sprocket_library_dir


_dialog_instance = None


def _freecad_main_window():
    try:
        import FreeCADGui as Gui

        return Gui.getMainWindow()
    except Exception:
        return None


class ASAUnifiedDialog(QtWidgets.QDialog):
    SINGLE_MODE = "single"
    CHAIN_MODE = "chain"
    DRIVE_MODE = "drive"

    def __init__(self, app_root, parent=None, initial_mode=None):
        super().__init__(parent)
        self.app_root = Path(app_root).resolve()
        self.chain_catalog_path = self.app_root / "data" / "chains" / "enco_asa_chains.csv"
        self.sprocket_catalog_dir = self.app_root / "data" / "sprockets" / "enco"
        self.library_dir = get_sprocket_library_dir()
        self.library_search_dirs = get_legacy_library_dirs(self.app_root)
        self.single_output_dir = self.library_dir
        self.drive_output_dir = get_output_dir()
        self.chain_catalog = load_catalog(self.chain_catalog_path)
        self.sprocket_catalog = load_enco_sprocket_catalog(self.sprocket_catalog_dir)
        self.last_calculation = None
        self.last_calculation_signature = None

        self.setWindowTitle("ASA Chain Drive — CAD Generator")
        self.setMinimumSize(760, 680)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self._build_ui()
        self._populate_asa()
        requested = self.mode_combo.findData(initial_mode)
        if requested >= 0:
            self.mode_combo.setCurrentIndex(requested)
        self._mode_changed()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("ASA / ANSI Parametric Generator")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "ASME B29.1 / ENCO sprocket or a complete rigid-link chain drive"
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        selection_box = QtWidgets.QGroupBox("Modeling type")
        selection_form = QtWidgets.QFormLayout(selection_box)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("Single sprocket", self.SINGLE_MODE)
        self.mode_combo.addItem("Rigid-link chain", self.CHAIN_MODE)
        self.mode_combo.addItem("Two sprockets connected by a chain", self.DRIVE_MODE)
        selection_form.addRow("Create:", self.mode_combo)
        self.asa_combo = QtWidgets.QComboBox()
        selection_form.addRow("Chain series:", self.asa_combo)
        layout.addWidget(selection_box)

        self.pages = QtWidgets.QStackedWidget()
        self.pages.addWidget(self._build_single_page())
        self.pages.addWidget(self._build_drive_page())
        layout.addWidget(self.pages)

        report_box = QtWidgets.QGroupBox("Engineering summary")
        report_layout = QtWidgets.QVBoxLayout(report_box)
        self.report = QtWidgets.QPlainTextEdit()
        self.report.setReadOnly(True)
        report_layout.addWidget(self.report)
        layout.addWidget(report_box, 1)

        button_layout = QtWidgets.QHBoxLayout()
        self.calculate_button = QtWidgets.QPushButton("Calculate Dimensions")
        self.calculate_button.setDefault(True)
        self.generate_button = QtWidgets.QPushButton("Generate Sprocket CAD")
        self.generate_button.setEnabled(False)
        self.close_button = QtWidgets.QPushButton("Close")
        button_layout.addWidget(self.calculate_button)
        button_layout.addWidget(self.generate_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        self.asa_combo.currentIndexChanged.connect(self._asa_changed)
        self.single_teeth_combo.currentIndexChanged.connect(self._single_changed)
        self.bore_spin.valueChanged.connect(self._inputs_changed)
        self.small_teeth_combo.currentIndexChanged.connect(self._drive_changed)
        self.large_teeth_combo.currentIndexChanged.connect(self._drive_changed)
        self.center_spin.valueChanged.connect(self._drive_changed)
        self.even_checkbox.stateChanged.connect(self._inputs_changed)
        self.calculate_button.clicked.connect(self._calculate)
        self.generate_button.clicked.connect(self._generate)
        self.close_button.clicked.connect(self.close)

    def _build_single_page(self):
        page = QtWidgets.QGroupBox("Single sprocket")
        form = QtWidgets.QFormLayout(page)
        self.single_teeth_combo = QtWidgets.QComboBox()
        form.addRow("Number of teeth:", self.single_teeth_combo)
        self.bore_spin = QtWidgets.QDoubleSpinBox()
        self.bore_spin.setDecimals(2)
        self.bore_spin.setSingleStep(0.5)
        self.bore_spin.setSuffix(" mm")
        form.addRow("Bore diameter:", self.bore_spin)
        return page

    def _build_drive_page(self):
        page = QtWidgets.QGroupBox("Chain drive")
        form = QtWidgets.QFormLayout(page)
        self.small_teeth_combo = QtWidgets.QComboBox()
        form.addRow("Small sprocket teeth (z1):", self.small_teeth_combo)
        self.large_teeth_combo = QtWidgets.QComboBox()
        form.addRow("Large sprocket teeth (z2):", self.large_teeth_combo)
        self.center_spin = QtWidgets.QDoubleSpinBox()
        self.center_spin.setRange(0.001, 1.0e7)
        self.center_spin.setDecimals(3)
        self.center_spin.setSingleStep(10.0)
        self.center_spin.setSuffix(" mm")
        self.center_spin.setValue(400.0)
        form.addRow("Desired center distance:", self.center_spin)
        self.minimum_center_label = QtWidgets.QLabel("Not calculated")
        minimum_font = self.minimum_center_label.font()
        minimum_font.setBold(True)
        self.minimum_center_label.setFont(minimum_font)
        form.addRow("Minimum center distance:", self.minimum_center_label)
        self.even_checkbox = QtWidgets.QCheckBox(
            "Require an even number of links (no offset link)"
        )
        form.addRow("", self.even_checkbox)
        return page

    def _available_asa(self):
        chain_sizes = {int(value) for value in self.chain_catalog if str(value).isdigit()}
        sprocket_sizes = set(
            get_available_asa_sizes(self.sprocket_catalog, strands=1, valid_only=True)
        )
        return sorted(chain_sizes & sprocket_sizes & set(ASME_SINGLE_FLANGE_WIDTH_MM))

    def _populate_asa(self):
        self.asa_combo.blockSignals(True)
        self.asa_combo.clear()
        for asa in self._available_asa():
            self.asa_combo.addItem(f"ASA {asa}-1", int(asa))
        self.asa_combo.blockSignals(False)
        if self.asa_combo.count() == 0:
            raise RuntimeError(
                "No ASA series has matching chain data, valid ENCO sprocket data, "
                "and an ASME flange width."
            )
        default_index = self.asa_combo.findData(80)
        self.asa_combo.setCurrentIndex(default_index if default_index >= 0 else 0)
        self._asa_changed()

    @staticmethod
    def _select_preferred(combo, preferred):
        index = combo.findData(int(preferred))
        if index < 0 and combo.count():
            index = 0
        combo.setCurrentIndex(index)

    def _asa_changed(self):
        asa = self.asa_combo.currentData()
        if asa is None:
            return
        teeth = get_available_teeth(
            self.sprocket_catalog, asa=int(asa), strands=1, valid_only=True
        )
        for combo in (
            self.single_teeth_combo,
            self.small_teeth_combo,
            self.large_teeth_combo,
        ):
            combo.blockSignals(True)
            combo.clear()
            for value in teeth:
                combo.addItem(str(value), int(value))
            combo.blockSignals(False)
        self._select_preferred(self.single_teeth_combo, 11)
        self._select_preferred(self.small_teeth_combo, 11)
        self._select_preferred(self.large_teeth_combo, 20)
        self._single_changed()
        self._drive_changed()

    def _mode_changed(self):
        single = self.mode_combo.currentData() == self.SINGLE_MODE
        self.pages.setCurrentIndex(0 if single else 1)
        labels = {
            self.SINGLE_MODE: "Generate Sprocket CAD",
            self.CHAIN_MODE: "Generate Chain CAD",
            self.DRIVE_MODE: "Generate Chain Drive CAD",
        }
        self.generate_button.setText(labels[self.mode_combo.currentData()])
        self._invalidate_calculation()
        if single:
            self._single_changed()
        else:
            self._drive_changed()

    def _chain_data(self):
        return get_chain_data(self.chain_catalog, int(self.asa_combo.currentData()))

    def _sprocket_data(self, teeth_combo):
        asa = int(self.asa_combo.currentData())
        teeth = teeth_combo.currentData()
        if teeth is None:
            raise RuntimeError("No valid number of teeth is selected.")
        return get_sprocket(
            self.sprocket_catalog,
            asa=asa,
            teeth_z=int(teeth),
            strands=1,
            manufacturer="ENCO",
            valid_only=True,
        )

    def _input_signature(self):
        mode = self.mode_combo.currentData()
        asa = self.asa_combo.currentData()
        if mode == self.SINGLE_MODE:
            return (
                mode,
                int(asa),
                int(self.single_teeth_combo.currentData()),
                round(float(self.bore_spin.value()), 6),
            )
        return (
            mode,
            int(asa),
            int(self.small_teeth_combo.currentData()),
            int(self.large_teeth_combo.currentData()),
            round(float(self.center_spin.value()), 6),
            bool(self.even_checkbox.isChecked()),
        )

    def _invalidate_calculation(self):
        self.last_calculation = None
        self.last_calculation_signature = None
        self.generate_button.setEnabled(False)
        self.calculate_button.setDefault(True)
        self.generate_button.setDefault(False)

    def _inputs_changed(self):
        self._invalidate_calculation()
        self.status_label.setText(
            "Inputs changed. Click Calculate Dimensions before generating CAD."
        )

    def _single_changed(self):
        self._invalidate_calculation()
        try:
            chain_data = self._chain_data()
            sprocket_data = self._sprocket_data(self.single_teeth_combo)
            pilot = float(sprocket_data["pilot_bore_mm"])
            maximum = float(sprocket_data["maximum_bore_mm"])
            self.bore_spin.blockSignals(True)
            self.bore_spin.setRange(pilot, maximum)
            self.bore_spin.setValue(pilot)
            self.bore_spin.blockSignals(False)
            self.report.setPlainText(
                "SINGLE SPROCKET — INPUTS\n"
                + "-" * 62
                + f"\nSeries: ASA {int(sprocket_data['asa'])}-1"
                + f"\nENCO reference: {sprocket_data['reference']}"
                + f"\nTeeth: {int(sprocket_data['teeth_z'])}"
                + f"\nPitch: {float(chain_data['pitch_P_mm']):.3f} mm"
                + f"\nAllowed bore: {pilot:.2f} to {maximum:.2f} mm"
                + "\n\nClick Calculate Dimensions to validate the geometry."
            )
            self.status_label.setText(f"Sprocket library: {self.single_output_dir}")
        except Exception as exc:
            self.report.setPlainText(f"ERROR\n\n{exc}")

    def _drive_changed(self):
        self._invalidate_calculation()
        try:
            chain_data = self._chain_data()
            small = self._sprocket_data(self.small_teeth_combo)
            large = self._sprocket_data(self.large_teeth_combo)
            physical_minimum = self._physical_minimum_center(small, large)
            self.center_spin.blockSignals(True)
            self.center_spin.setMinimum(physical_minimum + 0.001)
            self.center_spin.blockSignals(False)
            self.minimum_center_label.setText(f"> {physical_minimum:.3f} mm")
            self.minimum_center_label.setToolTip(
                "Half the sum of the two ENCO outside diameters."
            )
            self.report.setPlainText(
                "COMPLETE CHAIN DRIVE — INPUTS\n"
                + "-" * 62
                + f"\nSeries: ASA {int(self.asa_combo.currentData())}-1"
                + f"\nSmall sprocket: {int(small['teeth_z'])} teeth | {small['reference']}"
                + f"\nLarge sprocket: {int(large['teeth_z'])} teeth | {large['reference']}"
                + f"\nPitch: {float(chain_data['pitch_P_mm']):.3f} mm"
                + f"\nDesired center distance: {self.center_spin.value():.3f} mm"
                + f"\nMinimum center distance without solid overlap: > {physical_minimum:.3f} mm"
                + "\n\nClick Calculate Dimensions to solve the discrete chain length "
                + "and corrected center distance."
            )
            self.status_label.setText(
                f"Sprocket library: {self.library_dir}\nAssembly output: {self.drive_output_dir}"
            )
        except Exception as exc:
            self.minimum_center_label.setText("Unavailable")
            self.report.setPlainText(f"ERROR\n\n{exc}")

    @staticmethod
    def _physical_minimum_center(small, large):
        return 0.5 * (
            float(small["outside_diameter_mm"])
            + float(large["outside_diameter_mm"])
        )

    def _validate_drive_inputs(self, small, large):
        z1 = int(small["teeth_z"])
        z2 = int(large["teeth_z"])
        if z1 > z2:
            raise ValueError(
                "The small sprocket must have no more teeth than the large sprocket."
            )
        minimum = self._physical_minimum_center(small, large)
        if float(self.center_spin.value()) <= minimum:
            raise ValueError(
                f"The center distance must be greater than {minimum:.3f} mm "
                "to prevent the sprockets from overlapping."
            )
        return minimum

    def _calculate(self):
        self._invalidate_calculation()
        self.calculate_button.setEnabled(False)
        try:
            QtWidgets.QApplication.processEvents()
            if self.mode_combo.currentData() == self.SINGLE_MODE:
                calculation = self._calculate_single_dimensions()
            else:
                calculation = self._calculate_drive_dimensions()
            self.last_calculation = calculation
            self.last_calculation_signature = self._input_signature()
            self.generate_button.setEnabled(True)
            self.calculate_button.setDefault(False)
            self.generate_button.setDefault(True)
            self.status_label.setText(
                "Dimensions calculated and validated. CAD generation is enabled."
            )
        except Exception as exc:
            self.status_label.setText("Dimension calculation failed.")
            QtWidgets.QMessageBox.critical(self, "Dimension Calculation", str(exc))
        finally:
            self.calculate_button.setEnabled(True)

    def _calculate_single_dimensions(self):
        chain_data = self._chain_data()
        sprocket_data = self._sprocket_data(self.single_teeth_combo)
        geometry = calculate_asme_tooth_geometry(
            float(chain_data["pitch_P_mm"]),
            float(chain_data["roller_diameter_R_mm"]),
            int(sprocket_data["teeth_z"]),
        )
        pilot = float(sprocket_data["pilot_bore_mm"])
        maximum = float(sprocket_data["maximum_bore_mm"])
        outside = float(sprocket_data["outside_diameter_mm"])
        report = (
            "DIMENSION CALCULATION — SINGLE SPROCKET\n"
            + "-" * 62
            + f"\nSeries: ASA {int(sprocket_data['asa'])}-1"
            + f"\nENCO reference: {sprocket_data['reference']}"
            + f"\nNumber of teeth: {int(sprocket_data['teeth_z'])}"
            + f"\nChain pitch P: {float(chain_data['pitch_P_mm']):.3f} mm"
            + f"\nRoller diameter Dr: {float(chain_data['roller_diameter_R_mm']):.3f} mm"
            + f"\nPitch diameter PD: {geometry['PD']:.3f} mm"
            + f"\nOutside diameter DE: {outside:.3f} mm"
            + f"\nRoot diameter Ds: {geometry['Ds']:.3f} mm"
            + f"\nSeat radius R: {geometry['R']:.3f} mm"
            + f"\nSingle-strand flange width: {ASME_SINGLE_FLANGE_WIDTH_MM[int(sprocket_data['asa'])]:.3f} mm"
            + f"\nSelected bore: {self.bore_spin.value():.2f} mm"
            + f"\nAllowed bore range: {pilot:.2f} to {maximum:.2f} mm"
            + "\n\nGeometry standard: ASME B29.1 / GEARS construction"
            + "\nStatus: VALID — ready for CAD generation"
        )
        self.report.setPlainText(report)
        return {
            "mode": self.SINGLE_MODE,
            "chain_data": chain_data,
            "sprocket_data": sprocket_data,
            "geometry": geometry,
            "report": report,
        }

    def _calculate_drive_dimensions(self):
        chain_data = self._chain_data()
        small = self._sprocket_data(self.small_teeth_combo)
        large = self._sprocket_data(self.large_teeth_combo)
        minimum = self._validate_drive_inputs(small, large)
        pitch = float(chain_data["pitch_P_mm"])
        roller = float(chain_data["roller_diameter_R_mm"])
        small_geometry = calculate_asme_tooth_geometry(
            pitch, roller, int(small["teeth_z"])
        )
        large_geometry = calculate_asme_tooth_geometry(
            pitch, roller, int(large["teeth_z"])
        )
        result = calculate_discrete_chain_drive_geometry(
            pitch_mm=pitch,
            small_sprocket_teeth=int(small["teeth_z"]),
            large_sprocket_teeth=int(large["teeth_z"]),
            desired_center_distance_mm=float(self.center_spin.value()),
            require_even_link_count=bool(self.even_checkbox.isChecked()),
        )
        corrected = float(result["corrected_center_distance_mm"])
        if corrected <= minimum:
            raise ValueError(
                "The corrected center distance would make the sprockets overlap. "
                "Increase the desired center distance and calculate again."
            )
        center_correction = corrected - float(self.center_spin.value())
        offset_required = bool(result["requires_offset_link"])
        report = (
            "DIMENSION CALCULATION — COMPLETE CHAIN DRIVE\n"
            + "-" * 62
            + f"\nSeries: ASA {int(self.asa_combo.currentData())}-1"
            + f"\nChain pitch P: {pitch:.3f} mm"
            + f"\nRoller diameter Dr: {roller:.3f} mm"
            + "\n\nSMALL SPROCKET"
            + f"\n  ENCO reference: {small['reference']}"
            + f"\n  Teeth z1: {int(small['teeth_z'])}"
            + f"\n  Pitch diameter PD1: {small_geometry['PD']:.3f} mm"
            + f"\n  Outside diameter DE1: {float(small['outside_diameter_mm']):.3f} mm"
            + "\n\nLARGE SPROCKET"
            + f"\n  ENCO reference: {large['reference']}"
            + f"\n  Teeth z2: {int(large['teeth_z'])}"
            + f"\n  Pitch diameter PD2: {large_geometry['PD']:.3f} mm"
            + f"\n  Outside diameter DE2: {float(large['outside_diameter_mm']):.3f} mm"
            + "\n\nCENTER DISTANCE AND CHAIN CLOSURE"
            + f"\n  Minimum center distance: > {minimum:.3f} mm"
            + f"\n  Desired center distance: {self.center_spin.value():.3f} mm"
            + f"\n  Corrected center distance: {corrected:.3f} mm"
            + f"\n  Center-distance correction: {center_correction:+.3f} mm"
            + f"\n  Number of chain links: {int(result['link_count'])}"
            + f"\n  Offset link required: {'YES' if offset_required else 'NO'}"
            + f"\n  Chain closure residual: {float(result['closure_residual_mm']):.6e} mm"
            + "\n\nStatus: VALID — ready for CAD generation"
        )
        self.report.setPlainText(report)
        return {
            "mode": self.mode_combo.currentData(),
            "chain_data": chain_data,
            "small": small,
            "large": large,
            "minimum_center_distance_mm": minimum,
            "small_geometry": small_geometry,
            "large_geometry": large_geometry,
            "result": result,
            "report": report,
        }

    def _calculation_is_current(self):
        return (
            self.last_calculation is not None
            and self.last_calculation_signature == self._input_signature()
        )

    def _generate(self):
        if not self._calculation_is_current():
            self._invalidate_calculation()
            QtWidgets.QMessageBox.warning(
                self,
                "Calculate Dimensions",
                "Calculate and validate the current dimensions before generating CAD.",
            )
            return
        self.generate_button.setEnabled(False)
        try:
            QtWidgets.QApplication.processEvents()
            if self.last_calculation["mode"] == self.SINGLE_MODE:
                self._generate_single(self.last_calculation)
            else:
                self._generate_drive(self.last_calculation)
        except Exception as exc:
            self.status_label.setText("CAD generation failed.")
            QtWidgets.QMessageBox.critical(self, "ASA Chain Drive", str(exc))
        finally:
            self.generate_button.setEnabled(self._calculation_is_current())

    def _generate_single(self, calculation):
        chain_data = calculation["chain_data"]
        sprocket_data = calculation["sprocket_data"]
        self.status_label.setText("Generating and saving the sprocket...")
        QtWidgets.QApplication.processEvents()
        doc, sprocket, geometry, output_path, cache_hit = open_or_create_sprocket_document(
            chain_data=chain_data,
            sprocket_data=sprocket_data,
            bore_diameter_mm=float(self.bore_spin.value()),
            library_dir=self.library_dir,
            additional_search_dirs=self.library_search_dirs,
        )
        self.report.setPlainText(
            calculation["report"]
            + "\n\nCAD GENERATION COMPLETE\n"
            + "-" * 62
            + f"\nObject: {sprocket.Label}"
            + f"\nValid solid: {sprocket.Shape.isValid()}"
            + f"\nLibrary: {'reused existing item' if cache_hit else 'new item added'}"
            + f"\nFile: {output_path}"
        )
        self.status_label.setText(f"Sprocket saved to: {output_path}")
        QtWidgets.QMessageBox.information(
            self,
            "Sprocket Generated",
            f"The sprocket was generated successfully.\n\nFile:\n{output_path}",
        )

    def _generate_drive(self, calculation):
        from cad.chain_generator import generate_chain_drive_document

        result = calculation["result"]
        self.status_label.setText("Generating the sprockets, rigid links, and assembly...")
        QtWidgets.QApplication.processEvents()
        generated = generate_chain_drive_document(
            chain_data=calculation["chain_data"],
            result=result,
            output_dir=self.drive_output_dir,
            save=True,
            small_sprocket_data=(
                calculation["small"] if calculation["mode"] == self.DRIVE_MODE else None
            ),
            large_sprocket_data=(
                calculation["large"] if calculation["mode"] == self.DRIVE_MODE else None
            ),
            sprocket_library_dir=self.library_dir,
            sprocket_library_search_dirs=self.library_search_dirs,
        )
        output_path = generated["saved_path"]
        report = (
            calculation["report"]
            + "\n\nDISCRETE SOLVER DETAILS\n"
            + "-" * 62
            + "\n"
            + format_result_report(result)
            + "\n\nFREECAD ASSEMBLY\n"
            + "-" * 62
            + f"\nSmall sprocket: {generated['small_sprocket'].Label}"
            + f"\nLarge sprocket: {generated['large_sprocket'].Label}"
            + f"\nApp::Link instances: {len(generated['links'])}"
            + "\nSmall sprocket: "
            + ("reused from library" if generated["small_sprocket_cache_hit"] else "added to library")
            + "\nLarge sprocket: "
            + ("reused from library" if generated["large_sprocket_cache_hit"] else "added to library")
            + f"\nFile: {output_path}"
        )
        self.report.setPlainText(report)
        self.status_label.setText(f"Chain drive saved to: {output_path}")
        QtWidgets.QMessageBox.information(
            self,
            "Chain Drive Generated",
            "The complete chain drive was generated successfully.\n\n"
            f"File:\n{output_path}",
        )


def show_dialog(app_root, initial_mode=None):
    global _dialog_instance
    if _dialog_instance is not None:
        try:
            if _dialog_instance.isVisible():
                _dialog_instance.raise_()
                _dialog_instance.activateWindow()
                return _dialog_instance
        except Exception:
            pass
    _dialog_instance = ASAUnifiedDialog(
        app_root=app_root,
        parent=_freecad_main_window(),
        initial_mode=initial_mode,
    )
    _dialog_instance.show()
    _dialog_instance.raise_()
    _dialog_instance.activateWindow()
    return _dialog_instance
